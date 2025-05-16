function createReadToggleButton(emailId, readStatus, mailbox){
  const button = document.createElement('button');
  button.classList.add("btn", "btn-sm", "btn-outline-secondary");
  const label = readStatus ? "Mark as Unread" : "Mark as Read"
  button.innerHTML = label;

  button.onclick = function () {
    fetch(`/emails/${emailId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        read: !readStatus
      })
    })
    .then(response => {
      if (response.ok) {
        load_mailbox(mailbox);
      }
    });
  };
  return button;
}

function createArchiveToggleButton(emailId, isArchived, mailbox){
  const button = document.createElement("button");
  button.classList.add("btn", "btn-sm", "btn-outline-secondary");

  const newArchiveStatus = !isArchived; 
  button.innerHTML = newArchiveStatus ? "Add to Archive" : "Move to Inbox";

  button.onclick = function () {
    fetch(`/emails/${emailId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ archived: newArchiveStatus })
    })
    .then(response => {
      if (response.ok) {
        load_mailbox(mailbox); // reload the inbox after moving to inbox
      }
    })
  }
  return button;
}

function createEmailDiv(emailId, sender, subject, timestamp, isRead, isArchived, mailbox) {
  const emailDiv = document.createElement("div");
  emailDiv.style.border = "1px solid black"; 
  emailDiv.style.padding = "10px"; 
  emailDiv.style.marginBottom = "10px"; 

  emailDiv.style.background = isRead ? "rgba(169, 169, 169, 0.5)" : "rgba(255, 255, 255, 0.5)";

  emailDiv.innerHTML = `
    <a href="#" class="email-link" data-email-id="${emailId}">
      <strong>Sender:</strong> ${sender} <br>
      <strong>Subject:</strong> ${subject} <br>
      <strong>Timestamp:</strong> ${timestamp}
    </a>
    `;

  const markAsReadButton = createReadToggleButton(emailId, isRead, mailbox);
  emailDiv.appendChild(markAsReadButton);

  if (mailbox !== 'sent') {
    const archiveToggleButton = createArchiveToggleButton(emailId, isArchived, mailbox);
    emailDiv.appendChild(archiveToggleButton);
  }
  return emailDiv;
}

document.addEventListener('DOMContentLoaded', function() {

  // For top 3, if user clicks inbox button, for example, listen for it, and on click call load_mailbox, 
  // passing inbox as argument.  same for next 2.  for 4th one down, listen for compose button and 
  // call compose_mail function.  Bottom one is more complex, since the emails-view is dynamically 
  // rendered with emails from the server inside individual div tags, so we can't attach an event 
  // listener to dynamically rendered (and changing) html elements.  So we add the event listener to the 
  // parent (#emails-view) so that every div element dynamically renedered inside the emails-view parent
  // element can be dynamically accessed by the function associated with the event listener attached to 
  // the parent element.  event.target is like a "filter" that pinpoints the specific one of the 
  // dyanmically rendered child elements that was clicked on.  Then you check the classList with .contains
  // to be sure the child element is wrapped in the anchor tag with class 'email-link'.  Then go into the 
  // selected element and retrieve its data atatribute of data-email-id to get the email id# as a string.
  // then finish by calling the get_email method on the emailId
  document.querySelector('#inbox').addEventListener('click', () => load_mailbox('inbox'));
  document.querySelector('#sent').addEventListener('click', () => load_mailbox('sent'));
  document.querySelector('#archived').addEventListener('click', () => load_mailbox('archive'));
  document.querySelector('#compose').addEventListener('click', compose_email);
  document.querySelector('#emails-view').addEventListener('click', function(event) {
    if (event.target.classList.contains('email-link')) {
      const emailId = event.target.getAttribute('data-email-id');
      get_email(emailId);
    }
  });
  // Before any button is clicked, call load_mailbox, passing inbox to show user's mailbox to start 
  // session
  load_mailbox('inbox');
});

function get_email(emailId) { // dynamically render individual emails when you click on an email in mailbox
  // hide the emails-view (Inbox, sent, archive) and the compose-view and show individual-email-view
  document.querySelector("#emails-view").style.display = "none";
  document.querySelector("#individual-email-view").style.display = 'block';
  document.querySelector("#compose-view").style.display = "none";
  // clear any previously dynamically rendered emails
  const emailView = document.querySelector("#individual-email-view");
  emailView.innerHTML = "";
  // send an AJAX request of PUT method to server with a body of the request in string form setting
  // the read value to "true" to automatically signal that any clicked on email will by considered "read"
  fetch(`/emails/${emailId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      read: true  
    })
  });
  // send a get request to the server and convert response to a json object called emailData - which 
  // will be key:value pairs, with keys being columns of the Email model.
  fetch(`/emails/${emailId}`)
  .then(response => response.json())
  .then(emailData => {
    // select the entire element of id = individual-email-view and within that element, create a div
    // element called emailDetailsDiv to hold ind. email contents.  
    const emailView = document.querySelector("#individual-email-view");
    const emailDetailsDiv = document.createElement("div");
    // set innerHTML of newly created div element to the following values extracted from the returned
    // and converted JS object.  use .join for recipients, since it's value will be a list of strings.
    emailDetailsDiv.innerHTML = `
      <strong>From:</strong> ${emailData.sender} <br>
      <strong>To:</strong> ${emailData.recipients.join(", ")} <br>
      <strong>Subject:</strong> ${emailData.subject} <br>
      <strong>Timestamp:</strong> ${emailData.timestamp}
    `;

    const markAsReadButton = createReadToggleButton(emailId, true, 'inbox');
    emailView.appendChild(emailDetailsDiv);
    emailView.appendChild(markAsReadButton);

    // dynamically create a reply button for each individually rendered email and give it the same classes
    // as all the static buttons with .add  Make the button say "Reply"
    const replyButton = document.createElement("button");
    replyButton.classList.add("btn", "btn-sm", "btn-outline-primary");
    replyButton.innerHTML = "Reply";
    // Add event handler to the button so when it's clicked, emails-view and individual-email-views are
    // hidden and compose-view is shown to allow user to compose a reply
    replyButton.onclick = function() {
      document.querySelector('#emails-view').style.display = 'none';
      document.querySelector('#individual-email-view').style.display = 'none';
      document.querySelector('#compose-view').style.display = 'block';
      // autopopulate the recipients field with the sender of the eamil.  Note that we do not have to
      // autopopulate the sender field, since our view function does that.  Then autopoplulate the subject
      // field with the subject of the original email, prepending with "Re:" note that we're still within
      // the function assigned to the emailData object, so we still have access to its values
      document.querySelector('#compose-recipients').value = emailData.sender;
      document.querySelector('#compose-subject').value = `Re: ${emailData.subject}`;
      // to autopopulate the body of the reply with the original email body, pull the body, timestamp and
      // sender from the JS object emailData send from the server as a json response
      const originalBody = emailData.body;
      const timestamp = emailData.timestamp;
      const sender = emailData.sender;
      // create a string literal with interpolated data.  \n is escape for new line
      const quotedBody = `On ${timestamp}, ${sender} wrote:\n${originalBody}`;
      // populate the body textarea with the original email body
      document.querySelector('#compose-body').value = quotedBody;
    };
    // dynamically create a "Mark as Unread" button after the Reply button.  Give it same class as 
    // our other buttons.  It will say Mark as Unread, since all emails showing dynamically here will have
    // been considered "read" and their read status will have been set to "read" in the code above.

    // add an anonymous function to the button when clicked and send a PUT request to the server to update
    // read status to "false" to mark the email as "unread"
    markAsReadButton.onclick = function() {
    fetch(`/emails/${emailId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        read: false
      })
    })
      // if we get a response back from the server, call load_mailbox again to reload the inbox with
      // correct read/unread status for all emails in the mailbox
      .then(response => {
        if (response.ok) {
          load_mailbox('inbox');
        }
      });
    };
    // create an archive button and give it the same class as other buttons
    const archiveButton = document.createElement("button");
    archiveButton.classList.add("btn", "btn-sm", "btn-outline-secondary");
    // use the ternary operator ? to say if emailData archived property is true, do the first thing 
    // in quotes after the ? and if it's false, do the second thing in quotes after the colon
    archiveButton.innerHTML = emailData.archived ? "Remove from Archive" : "Add to Archive";
    // call an anonymous function on the archive button click and send a PUT request to the server to 
    // change the archived status to whatever it wasn't., then if we get a response back from the server
    // call load_mailbox again to show the inbox with updated archive status
    archiveButton.onclick = function() {
      fetch(`/emails/${emailId}`, {
        method: 'PUT',
        body: JSON.stringify({
          archived: !emailData.archived  
        })
      })
      .then(response => {
        if (response.ok) {
          load_mailbox('inbox');
        }
      });
    };
    // create a hr tag to make a break between header stuff and body of email
    const hrTag = document.createElement("hr");
    // create a div element for the body
    const bodyDiv = document.createElement("div");
    // populate the div tag with the body of the email - since we're still in the emailData function
    // with access to the JS object still!!
    bodyDiv.innerHTML = `
      ${emailData.body}
    `;
    // add all the newly created elements to the parent emailView div element
    emailView.appendChild(replyButton);
    emailView.appendChild(markAsReadButton);
    emailView.appendChild(archiveButton);
    emailView.appendChild(hrTag);
    emailView.appendChild(bodyDiv);
  });
}

function compose_email() {
  document.querySelector('#compose-form').onsubmit = function(event) {
    event.preventDefault();

    let data = {
      recipients: event.target.querySelector('#compose-recipients').value,
      subject: event.target.querySelector('#compose-subject').value,
      body: event.target.querySelector('#compose-body').value
    };
    // convert data (in dict form) to a byte string to send to server
    const jsonData = JSON.stringify(data);
    // send an AJAX request of POST method to the server, including the byte string in the body of the 
    // request
    fetch('/emails', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
      },
      body: jsonData, 
    })
    // get a resonse back, convert to a JS object and call it data
    .then(response => response.json())
    .then(data => {
      if (!data.error) {
        // if data was returned, call load_mailbox to show sent emails
        load_mailbox('sent');
      }
    });
  }

  // Show compose view and hide other views
  document.querySelector('#emails-view').style.display = 'none';
  document.querySelector('#compose-view').style.display = 'block';
  document.querySelector('#individual-email-view').style.display = 'none';

  // Clear out composition fields
  document.querySelector('#compose-recipients').value = '';
  document.querySelector('#compose-subject').value = '';
  document.querySelector('#compose-body').value = '';
}

function load_mailbox(mailbox) {
  // Show the mailbox (emails-view) and hide other views
  document.querySelector('#emails-view').style.display = 'block';
  document.querySelector('#compose-view').style.display = 'none';
  document.querySelector('#individual-email-view').style.display = 'none'; 

  // Clear existing name of mailbox and show the mailbox name
  const emailsView = document.querySelector("#emails-view");
  emailsView.innerHTML ="";

  emailsView.innerHTML += `<h3>${mailbox.charAt(0).toUpperCase() + mailbox.slice(1)}</h3>`;

  // dynamically send an http request to an API endpoint of our django mailbox view via 
  // path("emails/<str:mailbox>", views.mailbox, name="mailbox"),  the fetch will add mailbox dynamically
  // as either inbox, sent, or archive based on the event handlers above for the 3 buttons by setting
  // mailbox to either of these 3 values, then calling load_mailbox function of the chosen variable
  fetch(`/emails/${mailbox}`)
  // response.json will take the array of dicts returned by view function and convert it to a js array
  // and store it temporarily as response(promise), then the next line names "emails" as what that js 
  // arrary will be named from here on out
  .then(response => response.json())
  .then(emails => {
    // loop through each dict in the array and call the following arrow function - could also be an 
    // anonymous function here too, as emails.forEach(function(email) {.....})
    emails.forEach(email => {
      const emailDiv = createEmailDiv(
          email.id,           // emailId
          email.sender,       // sender
          email.subject,      // subject
          email.timestamp,    // timestamp
          email.read,         // isRead
          email.archived,     // isArchived
          mailbox             // pass the mailbox type (inbox, sent, archive)
        );
      
      emailsView.appendChild(emailDiv)
    });
  });
};

      
  
