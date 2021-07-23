from mailjet_rest import Client
from os import environ
from model import User


class MailManager:
    def __init__(self, app):
        api_key = app.config["MAILJET_API_KEY"]
        api_secret = app.config["MAILJET_API_SECRET"]
        self.client = Client(auth=(api_key, api_secret), version='v3.1')
        self.debug = app.debug

    def build_login_body(self, user, code):
        textpart = f'Pour te connecter, tu peux entrer le code: \n{code}'
        htmlpart = (
            f'<h3>Pour te connecter, entre le code suivant: {code}.</h3>'
            f'<br />A bientôt sur la martinade !'
        )
        return {
            'Messages': [
                {
                    "From": {
                        "Email": "noreply@martinade.fr",
                        "Name": "tristan"
                    },
                    "To": [{"Email": user.email, "Name": user.name}],
                    "Subject": "Authentifie toi à gallery.martinade.fr",
                    "TextPart": textpart,
                    "HTMLPart": htmlpart,
                    "CustomID": "AppGettingStartedTest"
                }
            ]
        }

    def send_login_mail(self, user, code):
        if not self.debug:
            data = self.build_login_body(user, code)
            result = self.client.send.create(data=data)
            return result.status_code == 200
        else:
            return True
