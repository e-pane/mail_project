import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'project3.settings'

import django
django.setup()

import pytest
from django.urls import reverse
from mail.models import User
from django.test import Client
import json
from .models import Email

@pytest.mark.django_db
def test_index_redirects_authenticated_user(client): # client object comes with .get() .post() .put() methods
    # to allow simulation of http requests from a browser to your view functions

    user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")

    client.login(username="testuser", password="password123")

    response = client.get(reverse("index"))

    assert response.status_code == 200
    assert b"inbox" in response.content.lower()

def test_index_redirects_unauthenticated_user(client):
    response = client.get(reverse("index"))

    assert response.status_code == 302
    assert response.url == reverse("login")

@pytest.mark.django_db
def test_compose_email(client): 

    user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
    recipient1 = User.objects.create_user(username="test_recipient1", email="recipient1@example.com", password="recipient1")
    recipient2 = User.objects.create_user(username="test_recipient2", email="recipient2@example.com", password="recipient2")

    client.login(username="testuser", password="password123")

    data = {
    "recipients": "recipient1@example.com, recipient2@example.com",
    "subject": "Test Subject",
    "body": "Test email body"
    }

    response = client.post(
                reverse("compose"),
                data=json.dumps(data),
                content_type="application/json",
               )

    assert response.status_code == 200 or response.status_code == 201

    email = Email.objects.first()

    assert email.subject == data["subject"]
    assert email.body == data["body"]

    assert set(email.recipients.values_list("email", flat=True)) == set([recipient1.email, recipient2.email])
  
@pytest.mark.django_db
def test_compose_no_recipients(client): # client object comes with .get() .post() .put() methods
    # to allow simulation of http requests from a browser to your view functions

    user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")

    client.login(username="testuser", password="password123")

    data = {
        "recipients": "",
        "subject": "Test Subject",
        "body": "Test email body"
    }

    response = client.post(
                reverse("compose"),
                data=json.dumps(data),
                content_type="application/json",
               )

    assert response.status_code == 400
    assert response.json()["error"] == "At least one recipient required."

@pytest.mark.django_db
def test_compose_invalid_recipient(client): # client object comes with .get() .post() .put() methods
    # to allow simulation of http requests from a browser to your view functions

    user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
    recipient = User.objects.create_user(username="validuser", email="validuser@example.com", password="validuser")

    client.login(username="testuser", password="password123")

    data = {
        "recipients": "validuser@example.com, invaliduser@example.com",
        "subject": "Test Subject",
        "body": "Test email body"
    }

    response = client.post(
                reverse("compose"),
                data=json.dumps(data),
                content_type="application/json",
               )

    assert response.status_code == 400
    assert response.json()["error"] == "User with email invaliduser@example.com does not exist."
    assert Email.objects.count() == 0

@pytest.mark.django_db
def test_compose_requires_login(client):

    # skip client.login(.....) step!!!!!

    data = {
    "recipients": "recipient1@example.com, recipient2@example.com",
    "subject": "Test Subject",
    "body": "Test email body"
    }

    response = client.post(
                reverse("compose"),
                data=json.dumps(data),
                content_type="application/json",
               )

    assert response.status_code in (302, 403)
    assert Email.objects.count() == 0

def test_compose_requires_post(client):

    user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")

    client.login(username="testuser", password="password123")

    response = client.get(reverse("compose"))
    assert response.status_code == 400
    assert response.json()["error"] == "POST request required."

def test_email_fetch_requires_login(client):
    # skip client.login(.....) step!!!!!
    response = client.get(reverse("email", kwargs= {"email_id": 1}))

    assert response.status_code in (302, 403)

@pytest.mark.django_db
def test_email_not_in_db(client):
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")

    client.login(username="testuser", password="password123")

    response = client.get(reverse("email", kwargs = {"email_id": 9999}))
    assert response.status_code == 404
    assert response.json()["error"] == "Email not found."

@pytest.mark.django_db
def test_email_in_db(client):
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
    

    client.login(username="testuser", password="password123")

    response = client.get(reverse("email", kwargs = {"email_id": 9999}))
    assert response.status_code == 404
    assert response.json()["error"] == "Email not found."

@pytest.mark.django_db
def test_archived_emails_visibility(client):
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
    recipient = User.objects.create_user(username="validuser", email="validuser@example.com", password="validuser")

    client.login(username="testuser", password="password123")

    email = Email(
        user=user,
        sender=user,
        subject="hello",
        archived=True
    )
    email.save()
    email.recipients.add(recipient, user)

    response = client.get(reverse("mailbox", kwargs={"mailbox": "archive"}))
    assert response.status_code == 200
    assert response.json()[0]["archived"] == True

@pytest.mark.django_db
def test_only_user_accesses_sent_mailbox(client):
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
    recipient = User.objects.create_user(username="validuser", email="validuser@example.com", password="validuser")

    client.login(username="testuser", password="password123")

    email1 = Email(
        user=user,
        sender=user,
        subject="hello",
        archived=True
    )
    email1.save()
    email1.recipients.add(recipient, user)

    email2 = Email(
        user=user,
        sender=recipient,
        subject="hello",
        archived=True
    )
    email2.save()
    email2.recipients.add(recipient, user)

    response = client.get(reverse("mailbox", kwargs={"mailbox": "sent"}))
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["sender"] == user.email

@pytest.mark.django_db
def test_put_toggles_read_status(client):
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
    recipient = User.objects.create_user(username="validuser", email="validuser@example.com", password="validuser")

    client.login(username="testuser", password="password123")

    email1 = Email(
        user=user,
        sender=user,
        subject="hello",
        read=False
    )
    email1.save()
    email1.recipients.add(recipient, user)

    response = client.put(reverse("email", kwargs = {"email_id": email1.id}),
                          data= json.dumps({"read":True}),
                          content_type = "application/json")   

    assert response.status_code == 204
    emails = Email.objects.filter(
            id = email1.id)
    assert emails[0].read is True

@pytest.mark.django_db
def test_put_toggles_archived_status(client):
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
    recipient = User.objects.create_user(username="validuser", email="validuser@example.com", password="validuser")

    client.login(username="testuser", password="password123")

    email1 = Email(
        user=user,
        sender=user,
        subject="hello",
        archived=False
    )
    email1.save()
    email1.recipients.add(recipient, user)

    response = client.put(reverse("email", kwargs = {"email_id": email1.id}),
                          data= json.dumps({"archived":True}),
                          content_type = "application/json")   

    assert response.status_code == 204
    emails = Email.objects.filter(
            id = email1.id)
    assert emails[0].archived is True