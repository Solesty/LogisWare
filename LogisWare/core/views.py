
import calendar
from datetime import date
from datetime import timedelta
from datetime import datetime
from dateutil.parser import parse
from django.utils.dateparse import parse_date
from django.db.models import Q
from django.contrib.auth import get_user_model, logout


from django.utils.crypto import get_random_string
import random
import string
from users.util import NewUserMessages

from django.utils import timezone

from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

from django.shortcuts import render, redirect
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from core.models import Client, Quote, Delivery, State, ReasonNotToDeliver

# Create your views here.


def index(request):

    return redirect('login')


def activate_user(request, pk):
    user = get_object_or_404(get_user_model(), pk=pk)
    user.is_active = True
    user.save()

    return redirect('dashboard_delivery_users')


def deactivate_user(request, pk):
    user = get_object_or_404(get_user_model(), pk=pk)
    user.is_active = False
    user.save()

    return redirect('dashboard_delivery_users')


@login_required
@require_http_methods(["POST"])
def create_new_user(request):

    email = request.POST.get('email', None)
    name = request.POST.get('name', None)
    user_type = request.POST.get('user_type', None)

    if (email is not None and len((str(email)).strip()) > 0) and ((name is not None) and len((str(name)).strip()) > 0) and (user_type is not None and len(str(user_type)) > 0):

        user_count = get_user_model().objects.filter(
            email=email
        ).count()

        if user_count == 0:
            new_user = get_user_model().objects.create(
                email=email,
                name=name,
                email_verified=False,
                is_super_admin=True
            )

            new_user.is_sales = False
            new_user.is_procurement = False
            new_user.is_delivery = False
            new_user.is_finance = False

            new_user.is_super_admin = False

            if user_type == 'SALES':
                new_user.is_sales = True
            elif user_type == 'PROCUREMENT':
                new_user.is_procurement = True
            elif user_type == 'DELIVERY':
                new_user.is_delivery = True

            new_user.save()

            user_password = generate_password()

            # send first time user mails
            new_user_messages_obj = NewUserMessages()
            new_user_messages_obj.send_welcome_message(
                new_user.email, new_user.name, None, new_user, user_password, request.user)

            new_user.set_password(
                user_password
            )
            new_user.save()

            messages.success(
                request,
                "An account has been created for " + name
            )
        else:
            messages.error(
                request,
                "A User with that email already exist."
            )
    else:
        messages.error(
            request,
            "The form details you supply wasn't enough."
        )

    return redirect('dashboard_delivery_users')


def generate_password():
    allowed_chars = ''.join((string.ascii_letters, string.digits))

    part_one = ''.join(random.choice(allowed_chars) for _ in range(5))
    part_two = get_random_string(length=5)

    return part_one + part_two


@login_required
def users_dashboard(request):
    users = get_user_model().objects.all().filter(
        ~Q(pk=request.user.pk)
    )

    context = {
        'users': users,
    }

    return render(request, 'core/delivery/users.html', context)

@login_required
def users_dashboard_procurement(request):
    users = get_user_model().objects.all().filter(
        ~Q(pk=request.user.pk)
    )

    context = {
        'users': users,
    }

    return render(request, 'core/procurement/users.html', context)


@login_required
@require_http_methods(['POST'])
def mark_items_not_delivered(request):
    quote_id = request.POST.get('quote_id', None)
    other_reasons = request.POST.get('other_reasons', None)
    reason = int(request.POST.get('reason', None))
    other_reasons = str(other_reasons).strip()

    if reason == -1 and len(other_reasons) == 0:
        messages.error(
            request, "What! Please write why you are not delivering the items"
        )
    else:
        reason_object = None
        quote = get_object_or_404(Quote, pk=quote_id)
        delivery = quote.delivery

        if reason > 0:
            reason_object = get_object_or_404(ReasonNotToDeliver, pk=reason)
            delivery.other_reasons = None
        else:
            delivery.other_reasons = other_reasons

        messages.success(
            request,
            "Your items has been marked not delivered"
        )

        delivery.delivered_by = None
        delivery.not_delivered_why = reason_object
        quote.status = 'NOTDELIVERED'
        quote.save()
        delivery.save()

    return redirect('dashboard_delivery')


@login_required
@require_http_methods(['GET'])
def update_quote_delivery(request, quote_pk, status_code):
    quote = get_object_or_404(Quote, pk=quote_pk)
    quote.status = status_code
    quote.save()

    if status_code == 'DELIVERED' or status_code == 'ITEM_RELEASED_CONFIRMED':
        delivery = quote.delivery
        delivery.date_delivered = timezone.now()
        delivery.delivered_by = request.user
        delivery.other_reasons = None
        delivery.not_delivered_why = None
        delivery.save()

    messages.success(request,
                     "The status of the quote has been successfuly changed to " + quote.get_status_display())

    return redirect('dashboard_delivery')


@login_required
def total_delivered(request):
    reasons = ReasonNotToDeliver.objects.all()

    total_deliveries = list(Quote.objects.filter(
        Q(status='DELIVERED') | Q(status='ITEM_RELEASED_CONFIRMED'),
        delivery__delivered_by=request.user
    ).order_by('-date_uploaded'))

    context = {
        'deliveries': total_deliveries,
        'reasons': reasons,
        'total_quotes': len(total_deliveries),
    }

    return render(request, 'core/delivery/alldeliveries.html', context)


@login_required
def not_delivered(request):
    reasons = ReasonNotToDeliver.objects.all()

    total_deliveries = Quote.objects.filter(
        Q(status='NOTDELIVERED'),
    )

    context = {
        'deliveries': total_deliveries,
        'reasons': reasons,
        'total_quotes': len(total_deliveries),
    }

    return render(request, 'core/delivery/alldeliveries.html', context)


@login_required
def todays_deliveries(request):
    reasons = ReasonNotToDeliver.objects.all()

    this_year = timezone.now().year
    this_day = timezone.now().day
    this_month = timezone.now().month

    start_date = date(this_year, this_month, this_day)
    end_date = start_date + timedelta(days=+1)

    total_deliveries = Quote.objects.filter(
        Q(status='AWAITDELIVERY') | Q(status='PARTIAL_ARRIVAL') |
        Q(status='ARRIVED') | Q(status='PARTIAL_DELIVERY'),
        # date_eta__day=this_day,
        # date_eta__month=this_month,
        # date_eta__year=this_year
        date_eta=start_date
    )

    context = {
        'deliveries': total_deliveries,
        'reasons': reasons,
        'total_quotes': len(total_deliveries),
    }

    return render(request, 'core/delivery/alldeliveries.html', context)


@login_required
def awaiting_deliveries(request):
    reasons = ReasonNotToDeliver.objects.all()

    total_deliveries = list(Quote.objects.filter(
        (Q(status='AWAITDELIVERY') | Q(status='PARTIAL_DELIVERY') | Q(status='ITEM_RELEASED')
         | Q(status='ARRIVED') | Q(status='PARTIAL_ARRIVAL')),
        #  | Q(status='PARTIAL_ARRIVAL') | Q(status='PARTIAL_DELIVERY')
        #  | Q(status='NOTDELIVERED')),
    ).order_by('-date_uploaded'))

    context = {
        'deliveries': total_deliveries,
        'reasons': reasons,
        'total_quotes': len(total_deliveries),
    }

    return render(request, 'core/delivery/alldeliveries.html', context)


@login_required
def days_deliveries_procurement(request, date_string):
    reasons = ReasonNotToDeliver.objects.all()

    date = parse(date_string)
    date = date + timedelta(+1)

    the_date = datetime(date.year, date.month, date.day)

    total_deliveries = list(Quote.objects.filter(
        date_eta=the_date
    ).order_by('-date_uploaded'))

    print(total_deliveries)

    for delivey in total_deliveries:
        print(delivey.date_eta.day)

    context = {
        'deliveries': total_deliveries,
        'reasons': reasons,
        'total_quotes': len(total_deliveries),
    }

    return render(request, 'core/procurement/all_deliveries.html', context)

@login_required
def days_deliveries(request, date_string):
    reasons = ReasonNotToDeliver.objects.all()

    date = parse(date_string)
    date = date + timedelta(+1)

    the_date = datetime(date.year, date.month, date.day)

    total_deliveries = list(Quote.objects.filter(
        date_eta=the_date
    ).order_by('-date_uploaded'))

    print(total_deliveries)

    for delivey in total_deliveries:
        print(delivey.date_eta.day)

    context = {
        'deliveries': total_deliveries,
        'reasons': reasons,
        'total_quotes': len(total_deliveries),
    }

    return render(request, 'core/delivery/alldeliveries.html', context)


@login_required
def all_deliveries(request):
    reasons = ReasonNotToDeliver.objects.all()

    total_deliveries = list(Quote.objects.filter(
        (Q(status='AWAITDELIVERY') | Q(status='DELIVERED')
         | Q(status='PARTIAL_ARRIVAL') | Q(status='PARTIAL_DELIVERY')
         | Q(status='NOTDELIVERED') | Q(status='ARRIVED'))
        | Q(status='ITEM_RELEASED') | Q(status='ITEM_RELEASED_CONFIRMED'),
        delivery__delivered_by=request.user
    ).order_by('-date_uploaded'))

    context = {
        'deliveries': total_deliveries,
        'reasons': reasons,
        'total_quotes': len(total_deliveries),
    }

    if (request.user.is_human_resource):
        return render(request, 'core/procurement/all_deliveries.html', context)
    else:
        return render(request, 'core/delivery/alldeliveries.html', context)


def get_calendar_events(quotes):
    # Loop through all the quote
    # Get the first date's quote and keep that date in a array
    # Go on and keep increasing the value of each date's by 1

    output = {}

    for quote in quotes:
        date_eta = quote.date_eta

        # // hmmm, I don't know why
        date_eta = date_eta + timedelta(+1)
        end_date_eta = date_eta + timedelta(+2)

        day = str(quote.date_eta.day)
        if len(day) == 1:
            day = "0" + day

        month = str(quote.date_eta.month)
        year = str(quote.date_eta.year)
        if len(month) == 1:
            month = "0" + month

        date_string = str(year) + "/" + str(month) + "/" + str(day)
        parsed_date = parse(date_string)
        # print(date_string)

        try:
            output[date_string]
            output[date_string] = int(output[date_string]) + 1
        except KeyError as identifier:
            output[date_string] = 1
        
        # print(output)

    delivery_sring = " Delivery"
    final_output = []
    for data in output:
        delivery_sring = " Delivery"
        if output[data] > 1:
            delivery_sring = " Deliveries"
            
        
        parsed_date = parse(str(data))
        # // hmmm, I don't know why
        date_eta = parsed_date + timedelta(+1)
        end_date_eta = parsed_date + timedelta(+2)
        
        print(parsed_date)

        day = str(date_eta.day)
        if len(day) == 1:
            day = "0" + day

        month = str(date_eta.month)
        year = str(date_eta.year)
        if len(month) == 1:
            month = "0" + month

        date_format = year + "-" + month + "-" + day
        end_date_format = str(end_date_eta.year) + "-" + \
            str(end_date_eta.month) + "-" + str(end_date_eta.day)
            
        

        item = {
            'title': str(output[data]) + delivery_sring,
            'start': date_format,
            'end': end_date_format,
            "count": output[data],
            "color": "darkblue"
        }
        final_output.append(item)

    return final_output

        # # I don't know why this is, but a day was deduceted
        # date_eta = date_eta + timedelta(+1)
        # end_date_eta = date_eta + timedelta(+2)

        # date_format = year + "-" + month + "-" + day
        # end_date_format = str(end_date_eta.year) + "-" + \
        #     str(end_date_eta.month) + "-" + str(end_date_eta.day)

        #     item = {
        #         'title': str(1) + delivery_sring,
        #         'start': date_format,
        #         'end': end_date_format,
        #         "count": date_items,
        #         "color": "red"
        #     }


@login_required
def dashboard_delivery(request):
    from datetime import datetime

    total_deliveries = list(Quote.objects.filter(
        Q(status='DELIVERED') |
        Q(status='ITEM_RELEASED_CONFIRMED'),
        delivery__delivered_by=request.user
    ).order_by('-date_uploaded'))

    this_year = timezone.now().year
    this_day = timezone.now().day
    this_month = timezone.now().month

    start_date = date(this_year, this_month, this_day)
    end_date = start_date + timedelta(days=+1)

    todays_deliveries = Quote.objects.filter(
        Q(status='PARTIAL_ARRIVAL') |
        Q(status='ARRIVED') |
        Q(status='AWAITDELIVERY') |
        Q(status='PARTIAL_DELIVERY') |
        Q(status='ITEM_RELEASED'),
        date_eta=start_date
    )

    tomorrow_deliveries_items = Quote.objects.filter(
        Q(status='PARTIAL_ARRIVAL') | Q(
            status='ARRIVED') | Q(status='PARTIAL_DELIVERY') |
        Q(status='ITEM_RELEASED'),
        date_eta__day=end_date.day,
        date_eta__month=end_date.month,
        date_eta__year=end_date.year
    )

    # Any quote that has arrived is automatically
    # waiting to be delivered

    awaiting_delivery_quotes = Quote.objects.filter(
        Q(status='PARTIAL_ARRIVAL') | Q(
            status='PARTIAL_DELIVERY') | Q(status='ARRIVED')
        | Q(status='AWAITDELIVERY')
        | Q(status='ITEM_RELEASED')
    )

    # print(awaiting_delivery_quotes)

    unattended_quptes = Quote.objects.filter(
        status='NOTDELIVERED'
    )

    all_deliverable_quotes = Quote.objects.filter(
    )

    current_date = None
    deliverables = []
    deliverables_event = []
    index = -1
    date_items = 0
    dates_worked = []

    deliverables_event = get_calendar_events(all_deliverable_quotes)
    
    import json
    deliverables_event = json.dumps(deliverables_event)

    context = {
        'now': timezone.now(),
        'tomorrow': end_date,
        'total_deliveries': len(total_deliveries),
        'deliverables': deliverables_event,
        'todays_deliveries_items': todays_deliveries,
        'tomorrow_deliveries_items': tomorrow_deliveries_items,
        'todays_deliveries': todays_deliveries.count(),
        'awaiting_arrival_quotes': awaiting_delivery_quotes.count(),
        'unattended_quptes': unattended_quptes.count(),
    }

    return render(request, 'core/delivery/dashboard.html', context)


# PROCUREENT

@login_required
def update_quote_prodcurement(request, quote_pk, status_code):
    quote = get_object_or_404(Quote, pk=quote_pk)
    quote.status = status_code
    quote.save()

    messages.success(request,
                     "The status of the quote has been successfuly changed to " + quote.get_status_display())

    return redirect('all_quotes_procurement')


@login_required
def dashboard_procurement(request):
    my_quotes = list(Quote.objects.all().order_by('-date_uploaded'))

    this_year = timezone.now().year
    this_day = timezone.now().day
    this_month = timezone.now().month

    start_date = date(this_year, this_month, this_day)
    end_date = start_date + timedelta(days=1)

    todays_quotes = Quote.objects.filter(
        date_uploaded__gte=start_date,
        date_uploaded__lte=end_date
    )

    awaiting_arrival_quotes = Quote.objects.filter(
        status='AWAARIVAL'
    )

    unattended_quptes = Quote.objects.filter(
        status='APRSNG'
    )
    
    # start 
    
    total_deliveries = list(Quote.objects.filter(
        Q(status='DELIVERED') |
        Q(status='ITEM_RELEASED_CONFIRMED'),
        delivery__delivered_by=request.user
    ).order_by('-date_uploaded'))

    this_year = timezone.now().year
    this_day = timezone.now().day
    this_month = timezone.now().month

    start_date = date(this_year, this_month, this_day)
    end_date = start_date + timedelta(days=+1)

    todays_deliveries = Quote.objects.filter(
        Q(status='PARTIAL_ARRIVAL') |
        Q(status='ARRIVED') |
        Q(status='AWAITDELIVERY') |
        Q(status='PARTIAL_DELIVERY') |
        Q(status='ITEM_RELEASED'),
        date_eta=start_date
    )

    tomorrow_deliveries_items = Quote.objects.filter(
        Q(status='PARTIAL_ARRIVAL') | Q(
            status='ARRIVED') | Q(status='PARTIAL_DELIVERY') |
        Q(status='ITEM_RELEASED'),
        date_eta__day=end_date.day,
        date_eta__month=end_date.month,
        date_eta__year=end_date.year
    )

    # Any quote that has arrived is automatically
    # waiting to be delivered

    awaiting_delivery_quotes = Quote.objects.filter(
        Q(status='PARTIAL_ARRIVAL') | Q(
            status='PARTIAL_DELIVERY') | Q(status='ARRIVED')
        | Q(status='AWAITDELIVERY')
        | Q(status='ITEM_RELEASED')
    )

    # print(awaiting_delivery_quotes)

    unattended_quptes = Quote.objects.filter(
        status='NOTDELIVERED'
    )

    all_deliverable_quotes = Quote.objects.filter(
    )

    current_date = None
    deliverables = []
    deliverables_event = []
    index = -1
    date_items = 0
    dates_worked = []

    deliverables_event = get_calendar_events(all_deliverable_quotes)
    
    import json
    deliverables_event = json.dumps(deliverables_event)

    context = {
        'now': timezone.now(),
        'tomorrow': end_date,
        'total_deliveries': len(total_deliveries),
        'deliverables': deliverables_event,
        'todays_deliveries_items': todays_deliveries,
        'tomorrow_deliveries_items': tomorrow_deliveries_items,
        'todays_deliveries': todays_deliveries.count(),
        'awaiting_arrival_quotes': awaiting_delivery_quotes.count(),
        'unattended_quptes': unattended_quptes.count(),

        'total_quotes': len(my_quotes),
        'todays_quotes': todays_quotes.count()
    }

    return render(request, 'core/procurement/dashboard.html', context)


@login_required
def unattended_quptes(request):

    unattended_quptes = Quote.objects.filter(
        status='APRSNG'
    )

    context = {
        'quotes': unattended_quptes,
        'total_quotes': len(unattended_quptes),
    }

    return render(request, 'core/procurement/allquotes.html', context)


@login_required
def awaiting_arrival_quotes(request):

    awaiting_arrival_quotes = Quote.objects.filter(
        status='AWAARIVAL'
    )
    
    context = {
        'quotes': awaiting_arrival_quotes,
        'total_quotes': len(awaiting_arrival_quotes),
    }

    return render(request, 'core/procurement/allquotes.html', context)


@login_required
def today_quotes_procurement(request):

    this_year = timezone.now().year
    this_day = timezone.now().day
    this_month = timezone.now().month

    start_date = date(this_year, this_month, this_day)
    end_date = start_date + timedelta(days=1)

    todays_quotes = Quote.objects.filter(
        date_uploaded__gte=start_date,
        date_uploaded__lte=end_date
    )
    context = {
        'quotes': todays_quotes,
        'total_quotes': len(todays_quotes),
    }

    return render(request, 'core/procurement/allquotes.html', context)


@login_required
def total_quotes_procurement(request):
    my_quotes = list(Quote.objects.all().order_by('-date_uploaded'))

    context = {
        'quotes': my_quotes,
        'total_quotes': len(my_quotes),
    }

    return render(request, 'core/procurement/allquotes.html', context)


@login_required
def all_quotes_procurement(request):
    my_quotes = list(Quote.objects.all().order_by('-date_uploaded'))

    context = {
        'quotes': my_quotes,
        'total_quotes': len(my_quotes),
    }

    return render(request, 'core/procurement/allquotes.html', context)

# SALES


@login_required
def sales_dashboard(request):

    total_quotes = Quote.objects.filter(
        manager=request.user
    ).count()

    whole_quotes = Quote.objects.filter(
        manager=request.user
    )

    done_deals = 0
    pending_items = 0
    total_sales = 0.0
    item_delivered = 0
    months_data = []

    # get total number done deals for each month
    this_year = timezone.now().year
    for i in range(1, 13):
        total_days = calendar.monthrange(this_year, i)[1]
        start_date = date(this_year, i, 1)

        end_date = date(this_year, i, total_days)
        months_quote = Quote.objects.filter(
            (Q(status='PAID_DELIVER') | Q(status='AWAITDELIVERY') | Q(status='PARTIAL_ARRIVAL')
             | (Q(status='DELIVERED') | Q(status='NOTDELIVERED'))) | Q(status='ITEM_RELEASED_CONFIRMED'),
            date_uploaded__gte=start_date,
            date_uploaded__lte=end_date,
            manager=request.user,
        )
        months_data.append(months_quote.count())

    for quote in whole_quotes:
        if quote.status in ['PAID_DELIVER', 'AWAITDELIVERY', 'DELIVERED', 'NOTDELIVERED', 'PARTIAL_ARRIVAL', 'ITEM_RELEASED_CONFIRMED']:
            item_delivered = item_delivered + 1
            done_deals = done_deals + 1

        else:
            pending_items = pending_items + 1

    context = {
        'months_data': months_data,
        'total_quotes': total_quotes,
        'done_deals': done_deals,
        'pending_items': pending_items,
        'total_sales': total_sales,
    }

    return render(request, 'core/sales/dashboard.html', context)


@login_required
def done_deals_sales(request):
    my_quotes = Quote.objects.filter(
        (Q(status='PAID_DELIVER') | Q(status='AWAITDELIVERY') | Q(status='PARTIAL_ARRIVAL')
         | (Q(status='DELIVERED')))
        | (Q(status='ITEM_RELEASED_CONFIRMED')),
        manager=request.user,
    )

    context = {
        'quotes': my_quotes,
        'total_quotes': len(my_quotes),
    }

    return render(request, 'core/sales/allquotes.html', context)


@login_required
def pending_items_sales(request):
    my_quotes = Quote.objects.filter(
        (Q(status='AWAITDELIVERY') | Q(status='PARTIAL_ARRIVAL') | Q(status='APRSNG')
         | (Q(status='NOTDELIVERED')))
        | (Q(status='ITEM_RELEASED')),
        manager=request.user,
    )

    context = {
        'quotes': my_quotes,
        'total_quotes': len(my_quotes),
    }

    return render(request, 'core/sales/allquotes.html', context)


@login_required
def all_quotes_sales(request):
    my_quotes = list(Quote.objects.filter(
        manager__id=request.user.id
    ).order_by('-date_uploaded'))

    context = {
        'quotes': my_quotes,
        'total_quotes': len(my_quotes),
    }

    if(request.user.is_procurement):
        return render(request, 'core/procurement/allquotes.html', context)
    else:
        return render(request, 'core/sales/allquotes.html', context)


@login_required
def delete_quote(request, pk):
    pass


def delete_quote_item(request, pk, qid):
    quote_item = get_object_or_404(QuoteItem, pk=pk)
    quote = get_object_or_404(Quote, pk=qid)

    if quote_item.quote_item_status == 'APRSNG':
        quote_item.delete()

        messages.success(
            request,
            "Quote Item has been successfully deleted"
        )
    else:
        messages.error(
            request,
            "You can not delete a quote that has already been marked processed"
        )

    return redirect('/quotes/items/' + str(quote.id))


# class QuoteView(ListView):
#     model = QuoteItem

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(self, **kwargs)

#         return context

class QuoteDetailView(DetailView):
    model = Quote
    template_name = 'core/sales/quote_items.html'
    context_object_name = 'quote'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context


@login_required
def extend_eta(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    new_eta = request.POST['new_eta']

    # expected year-mm-dd
    new_eta = parse_date(new_eta)
    old_quote_date = str(quote.date_eta.year) + "-" + \
        str(quote.date_eta.month) + "-" + str(quote.date_eta.day)

    if quote.new_eta_set == True:
        old_new_eta = str(quote.new_eta.year) + "-" + \
            str(quote.new_eta.month) + "-" + str(quote.new_eta.day)
        if parse(str(new_eta)) < parse(old_new_eta):
            messages.error(
                request, "Your new eta needs to be set to a future date.")
            referer_page = request.META['HTTP_REFERER']
            # if referer_page not None:
            return redirect(referer_page)

    if parse(str(new_eta)) > parse(old_quote_date):
        quote.new_eta = new_eta
        quote.new_eta_set = True
        quote.save()
        messages.success(request, "Quote has been modified")
    else:
        messages.error(
            request, "Your new eta needs to be set to a future date.")

    referer_page = request.META['HTTP_REFERER']
    # if referer_page not None:
    return redirect(referer_page)


@login_required
def edit_quote(request, pk):
    states = State.objects.all()
    my_quote = get_object_or_404(Quote, pk=pk)

    context = {
        'quote': my_quote,
        'states': states,
    }

    return render(request, 'core/sales/edit_quote.html', context)


@login_required
def add_quotes_sales(request):
    states = State.objects.all()
    my_quotes = list(Quote.objects.filter(
        manager__id=request.user.id
    ).order_by('-date_uploaded'))

    context = {
        'quotes': my_quotes,
        'total_quotes': len(my_quotes),
        'states': states,
    }

    return render(request, 'core/sales/addquote.html', context)


class AllClientView(ListView):
    model = Client
    template_name = 'core/procurement/all_clients.html'
    context_object_name = 'clients'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        the_clients = []
        if self.request.user.is_authenticated == True:
            clients = Client.objects.all()
            for client in clients:
                found = False
                for picked_client in the_clients:
                    if picked_client.email == client.email:
                        found = True
                        break
                if found == False:
                    the_clients.append(client)

        context = {
            "clients": the_clients
        }

        return context


class ClientView(ListView):
    model = Client
    template_name = 'core/sales/clients.html'
    context_object_name = 'clients'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        my_quotes = list(Quote.objects.filter(
            manager__id=self.request.user.id
        ).order_by('-date_uploaded'))
        
        
        my_quotes = Quote.objects.filter(
            manager = self.request.user
        )
        
        the_clients = []
        if self.request.user.is_authenticated == True:
            clients = Client.objects.all()
            for quote in my_quotes:
                found = False
                for picked_client in the_clients:
                    if picked_client.email == quote.client.email:
                        found = True
                        break
                if found == False:
                    the_clients.append(quote.client)
            
        # print(the_clients)

        context = {
            "clients": the_clients
        }

        context['total_quotes'] = len(my_quotes)

        return context


@login_required
@require_http_methods(['POST'])
def edit_quote_apply(request, pk):
    contact_name = str(request.POST.get('contact_name', None)).strip()
    phone_one = request.POST.get('phone_one', None)
    # company_name = request.POST.get('company_name', None)
    email = request.POST.get('email', None)
    delivery_type = request.POST.get('delivery_type', None)
    delivery_location = request.POST.get('delivery_location', None)
    delivery_state = request.POST.get('delivery_state', None)

    quote_number = str(request.POST.get('quote_number', None)).strip()
    description = request.POST.get('description', None)

    # part_numbers = request.POST.getlist('part_numbers[]', [])
    # descriptions = request.POST.getlist('descriptions[]', [])
    # quantities = request.POST.getlist('quantities[]', [])
    # unit_prices = request.POST.getlist('unit_prices[]', [])

    quote = get_object_or_404(Quote, pk=pk)

    if (
        (delivery_type is not None and len(delivery_type) > 0) and
        (delivery_location is not None and len(delivery_location) > 0) and
        (quote_number is not None and len(quote_number) > 0) and
        (contact_name is not None and len(contact_name) > 0) and
        (phone_one is not None and len(phone_one) > 0)
    ):

        # Save the client detail
        client = Client()
        # client.company_name = company_name
        client.email = email
        client.name = contact_name
        client.phone_one = phone_one
        client.save()

        # Store the quote
        quote.client = client
        quote.quote_number = quote_number
        quote.description = description

        state = 0
        try:
            state = State.objects.get(
                pk=delivery_state
            )
        except State.DoesNotExist:
            pass

        delivery = Delivery()
        delivery.delivery_location = delivery_location
        delivery.delivery_type = delivery_type
        delivery.delivery_state = state
        delivery.save()

        quote.delivery = delivery
        quote.save()

        messages.success(
            request,
            "Your Quote has been modified"
        )

        if(request.user.is_procurement):
            return redirect('all_quotes_procurement')
        else:
            return redirect('all_quotes_sales')

    else:
        messages.error(
            request,
            "Please all the fields with asterisk must be filled. Thanks"
        )
        return redirect('edit_quote')


@login_required
@require_http_methods(['POST'])
def insert_quote(request):
    contact_name = str(request.POST.get('contact_name', None)).strip()
    phone_one = request.POST.get('phone_one', None)
    # company_name = request.POST.get('company_name', None)
    email = request.POST.get('email', None)
    delivery_type = request.POST.get('delivery_type', None)
    delivery_location = request.POST.get('delivery_location', None)
    delivery_state = request.POST.get('delivery_state', None)

    quote_number = str(request.POST.get('quote_number', None)).strip()
    eta = request.POST.get('eta', None)
    description = request.POST.get('description', None)

    # part_numbers = request.POST.getlist('part_numbers[]', [])
    # descriptions = request.POST.getlist('descriptions[]', [])
    # quantities = request.POST.getlist('quantities[]', [])
    # unit_prices = request.POST.getlist('unit_prices[]', [])

    if (
        (delivery_type is not None and len(delivery_type) > 0) and
        (delivery_location is not None and len(delivery_location) > 0) and
        (quote_number is not None and len(quote_number) > 0) and
        (contact_name is not None and len(contact_name) > 0) and
        (eta is not None and len(eta) > 0) and
        (phone_one is not None and len(phone_one) > 0)
    ):

        # expected year-mm-dd
        date_eta = parse_date(eta)

        if(date.today() > date_eta):
            messages.error(
                request,
                "The ETA can not be in the past (" + str(date_eta.month) + "/" + str(
                    date_eta.day) + "/" + str(date_eta.year) + ")"
            )
            return redirect('add_quotes_sales')

        # Save the client detail
        client = Client()
        # client.company_name = company_name
        client.email = email
        client.name = contact_name
        client.phone_one = phone_one
        client.save()

        # Store the quote
        quote = Quote()
        quote.client = client
        quote.date_eta = date_eta
        quote.manager = request.user
        quote.quote_number = quote_number
        quote.description = description

        state = 0
        try:
            state = State.objects.get(
                pk=delivery_state
            )
        except State.DoesNotExist:
            pass

        delivery = Delivery()
        delivery.delivery_location = delivery_location
        delivery.delivery_type = delivery_type
        delivery.delivery_state = state
        delivery.save()

        quote.delivery = delivery
        quote.save()

        messages.success(
            request,
            "Your Quote has been saved"
        )

        if(request.user.is_procurement):
            return redirect('all_quotes_procurement')
        else:
            return redirect('all_quotes_sales')

    else:
        messages.error(
            request,
            "Please all the fields with asterisk must be filled. Thanks"
        )
        return redirect('add_quotes_sales')
