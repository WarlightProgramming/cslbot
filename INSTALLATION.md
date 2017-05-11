# Deploying cslbot

Deploying cslbot is relatively simple. While the original code is configured to
run on Google Cloud Platform, you're free to use whatever cloud host (or other
server solution) you want. The top-level Flask app in main.py handles the API
and you can use either the /run endpoint or the run() function in run.py to
run the Bot.

Note that you don't need to set up and deploy cslbot (or any Bot) just to run a
Cluster. Clusters can work with any Interface and any Bot, so deploying a new
Bot and/or a new Interface for every Cluster or league is redundant and
counterproductive.

## Clone

1. Clone the source code of this project, using either git clone or installing
   the zip file for the latest release or the current master branch.

## Credentials

1. **Warlight credentials.** Create a JSON file with the keys 'E-mail' and
   'APIToken' that correspond to the e-mail and API token for a Warlight Member
   account. Note that you have to be a Warlight Member to deploy a Bot or
   serve as the admin for a Cluster.

2. **Google Sheets credentials.** Using the instructions [found here](http://gspread.readthedocs.io/en/latest/oauth2.html),
   obtain Google Sheets OAuth credentials and store that JSON file somewhere
   else in the cslbot directory.

## Configure

1. Update the values in the resources/constants.py file to refer to the correct
   file locations for your credentials (file locations should be from the
   perspective of the top-level cslbot directory).

2. Generate your own debug key and update the DEBUG\_KEY value in
   resources/constants.py. Note that this value isn't a perfect safeguard and
   most of the security/abuse prevention happens through obfuscation, but a
   sufficiently motivated user can easily get the debug key without going
   through you. Feel free to set it to just "DEBUG MODE" for simplicity.

3. Create a spreadsheet and share it with the service account for your Google
   Sheets credentials. Get the ID of that spreadsheet (in the URL, between
   /edit/ and /d/) and set GLOBAL\_MANAGER to that ID.

4. Change the OWNER\_ID to your own Warlight ID.

5. **If you're using Google App Engine:** using virtualenv and pip or some other tools, install the libraries in
   requirements.txt to a folder within the cslbot top-level directory. Check
   appengine\_config.py and make sure you're referring to that folder for
   libraries. **If you're using another server solution**, make sure you've got
   the libraries in requirements.txt installed somewhere that they can be used
   by your application.

## Deploy

1. Set up a server to host this web application and to frequently run all
   leagues (using either the /run endpoint or the run() function in run.py- you
   can simply use python run.py to call that function constantly).

2. Go to Warlight's [CLOT authentication configuration](https://www.warlight.net/clot/config)
   and update your CLOT redirect URL to the /login endpoint of your cslbot web
   app. If you've already got another redirect URL, create a portal at that URL
   that uses the 'state' parameter to route traffic to the cslbot /login
   endpoint and/or your other /login endpoints. Note that any request sent to
   your CLOT authentication URL has its 'state' parameter preserved by
   Warlight so you can store any arbitrary information in that parameter.

## Debug

1. Given that different cloud hosts have their quirks, be sure to test out your
   application and make sure it works. You may have to add some monkey patches
   in the code. (Feel free to open PRs with those monkey patches so that the
   cslbot project as a whole can benefit.)
