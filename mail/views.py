import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import HttpResponse, HttpResponseRedirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .models import User, Email


def index(request):

    # Authenticated users view their inbox
    if request.user.is_authenticated:
        return render(request, "mail/inbox.html")

    # Everyone else is prompted to sign in
    else:
        return HttpResponseRedirect(reverse("login"))


@csrf_exempt
@login_required
def compose(request):

    # Composing a new email must be via POST.  Note the form submission is not via post method - like we
    # usually would - because we're writing js to intercept the form submission and package form data 
    # as request.body, packaged inside the body of the http request, which becomes a POST request.  Since
    # there's no explicit POST method in the index.html form coming here, it will default to GET method
    # without JS to intercept and convert the form data to request.body
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)

    # Check recipient emails, request.body is the incoming form data in a js-intercepted format, where js
    # is preventing a regular form submission and packaging form data instead as a json response in 
    # byte string format. json.loads converts that byte string to a Python dictionary called "data"
    data = json.loads(request.body)
    # data will likely have recipients as a dict key and a string of potentially several email addresses
    # separated by commas  . get will pull the string and .split will split the multiple recipient addresses 
    # by commas and put them in a lazy list.  Iterate over that list of strings and use .strip on each
    # string to strip the white space.  then the [] bracketing the whole expression will make a list of
    # the individual address strings
    emails = [email.strip() for email in data.get("recipients").split(",")]
    if emails == [""]:
        return JsonResponse({
            "error": "At least one recipient required."
        }, status=400)

    # Convert email addresses to users.  initialize an empty list of user instances
    recipients = []
    # loop over the string addresses in the list "emails"
    for email in emails:
        try:
            # with email as a string of the address, straight up query the User model for the instance 
            # where that user's email address matches each string pulled from the list.  Remember that 
            # User(AbstractUser) has AbstractUser as a subclass that would have fields of name, email, pword..
            # and .get because we want only one instance not a q-set of instances (use .filter for that)
            user = User.objects.get(email=email)
            # add the user instance to the recipients list
            recipients.append(user)
        except User.DoesNotExist:
            # note here and the previous 2 JsonResponse rendering will go to inbox.js (since it's our
            # only js file to receive a JsonRespons!!). the json response is a dict with one key and one
            # value and the json response construtor will also take the status=400 parameter as an 
            # argument to help attach the corret error code to the overall http response containing this
            # JsonResponse
            return JsonResponse({
                "error": f"User with email {email} does not exist."
            }, status=400)

    # Since json.loads() made a dict of the form data, index into the subject and body keys to get the
    # string values of both
    subject = data.get("subject", "")
    body = data.get("body", "")

    # Create one email for each recipient, plus sender
    # initialize an empty set (set to ensure uniqueness of users)
    users = set()
    # to the empty set, add the user instance for the authenticated user (who is the sender) using 
    # request.user  Note that .add is to add only one thing to a set
    users.add(request.user)
    # use .update to add all of the user instances in recipients to the set at one time
    users.update(recipients)
    # loop through the set of instances, one instance at a time and instantiate an instance of the Email
    # model for each instance, adding an instance, instance, string, string and Bool, respectively.  user
    # and sender must be instances (bc they're foreign keys fields in the model), subject and body are
    # simple "string" fields, Char and Text, respectively, and read takes a Bool, where user==request.user
    # is asking if the user (sender) instance is the same as the authenticated user instance - which will
    # be true, and which is sort of assuming any sender will have "read" their sent email.  But the other
    # recipients won't have immediately read the email, so they're read field will default (as per the 
    # model field) to false until they actually read it.  No timestamp field needed due to autofill by
    # django and no archived field, as it will default (per the model field) to false until overridden
    # and recipients must be a q-set (manytomany field) and you can construct q-sets in this way.  so 
    # just below you'll see the manual addition of the q-set to each instance
    for user in users:
        email = Email(
            user=user,
            sender=request.user,
            subject=subject,
            body=body,
            read=user == request.user
        )
        email.save()
        # then loop through the list of instances called recipients and for each instance, add it to the
        # secret squirrel email.recipients join table.  then email.recipients can become a related manager
        # that uses the .add method to add each recipient instance in the list to the email.recipients
        # join table.  This join table will manytomany connect to the Email table.
        for recipient in recipients:
            email.recipients.add(recipient)
        email.save()

    return JsonResponse({"message": "Email sent successfully."}, status=201)


@csrf_exempt
@login_required
def email(request, email_id): # to display an individual email, accepting email_id as incoming parameter
    # path("emails/<int:email_id>", views.email, name="email"), so expect the js to have something like
    # fetch(`/emails/${email_id}`,...) if you click on email in the model with id = 100, the url will 
    # become /emails/100  
    try:
        # get the instance of just this email from the table matching user instance and incoming email_id
        email = Email.objects.get(user=request.user, pk=email_id)
    except Email.DoesNotExist:
        return JsonResponse({"error": "Email not found."}, status=404)

    # Return email contents of that particular email the user clicked on.  call the serialize method 
    # on the specific instance retrieved to convert the instance to json object that's an array of dicts
    # as part of the jsonResponse
    if request.method == "GET":
        return JsonResponse(email.serialize())

    # Update whether email is read or should be archived.  PUT method will come from js fetch call with 
    # method = PUT this js will be an event listener when I put a mark as read and archive button within
    # the inbox.html view for a single email to be displayed.  Then the JS will also have to intercept
    # the http request and convert it form data to byte string, then the .loads will convert that byte
    # string to a python dictionary for us.  Incoming byte string will just be read: true, archived: false
    # or some combination thereof  
    elif request.method == "PUT":
        data = json.loads(request.body)
        # if there is a read key:value pair, we'll change read field value of email model to true of false
        # depending on the incoming read value. and the js will set that value based on index.html
        # which will need to conditionally display "mark as read" or "mark as unread".  same for archive
        if data.get("read") is not None:
            email.read = data["read"]
        if data.get("archived") is not None:
            email.archived = data["archived"]
        email.save()
        return HttpResponse(status=204)

    # Email must be via GET or PUT
    else:
        return JsonResponse({
            "error": "GET or PUT request required."
        }, status=400)


def login_view(request): # all 3 of the following view functions are boilerplate and same as found in 
    # project 2 auctions
    if request.method == "POST":

        # Attempt to sign user in
        email = request.POST["email"]
        password = request.POST["password"]
        user = authenticate(request, username=email, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "mail/login.html", {
                "message": "Invalid email and/or password."
            })
    else:
        return render(request, "mail/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))

@login_required
def mailbox(request, mailbox): # to return a dynamically variable JsonResponse to inbox.js based on the
    # value of the incoming mailbox parameter.  If our js has fetch(`/emails/${mailbox}`...`) and mailbox
    # is set to "inbox" in our js code, then mailbox
    # will evaluate to inbox and the first conditional will be true.  same for fetch("emails/sent",..) bc
    # the url path will have ("emails/<str:mailbox>", views.mailbox, name="mailbox")

    if mailbox == "inbox":
        # fetch q-set of instances from Email table where user instance is that of the authenticated user,
        # and archived field is False.  Regarding the filter: recipients=request.user this is troubling
        # bc request.user is an instance, but recipients is a query set, but apparently django can 
        # figure out that this means pull a queryset of all instances from the Email_recipients table 
        # where the user is the recipient.  So emails is a queryset
        emails = Email.objects.filter(
            user=request.user, recipients=request.user, archived=False
        )
    elif mailbox == "sent":
        # fetch q-set of instances where sender instances = instances for the authenticated user
        emails = Email.objects.filter(
            user=request.user, sender=request.user
        )
    elif mailbox == "archive":
        # fetch q-set of instances matching that from "inbox" conditional above, but switch to only 
        # those instances where archived field evaluates to True
        emails = Email.objects.filter(
            user=request.user, recipients=request.user, archived=True
        )
    else:
        return JsonResponse({"error": "Invalid mailbox."}, status=400)

    # Return the instances in the q-set in reverse chronologial order using .order_by method and 
    # -timestamp for reverse. this is just ordering the instance in the q-set that's already built, 
    # so I really don't think .all() is needed here???
    emails = emails.order_by("-timestamp").all()
    # loop through through the instances of the q-set and call .serialize (custom method of the Email
    # model) on each instance to convert each instance to a dictionary, within a json array(list).  Note
    # need to set safe property to False bc jsonResponse will be expecting a dict and with safe=False, it
    # will reject the list(array) we're sending it
    return JsonResponse([email.serialize() for email in emails], safe=False)

def register(request):
    if request.method == "POST":
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "mail/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(email, email, password)
            user.save()
        except IntegrityError as e:
            print(e)
            return render(request, "mail/register.html", {
                "message": "Email address already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "mail/register.html")
