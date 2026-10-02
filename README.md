# Polite Email Generator

**Describe what you need to say, and AI writes it as a polite, well-structured email.**

We built this in one weekend at the **EESTEC Hackathon 2022**. Writing emails that are clear and also kind takes time, especially when the topic is awkward. You enter who the email is for, their organisation, what you need and your signature. The app drafts a polite email with a proper opening and closing, which you can accept or reject.

## How it works

1. A small Flask web app collects four fields: recipient, affiliation, purpose and signature.
2. The fields go into a prompt that asks the model for a polite, constructive email without harsh wording.
3. OpenAI's GPT-3 (`text-davinci-002`) writes the draft, and the app shows it on the page.

## Tech

Python · Flask · OpenAI API · HTML and CSS

## Run it locally

```bash
git clone https://github.com/evavid/polite-email-generator.git
cd polite-email-generator
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then add your OPENAI_API_KEY
flask run
```

Then open http://127.0.0.1:5000.

> **Note:** this is the 2022 hackathon version. It uses the legacy OpenAI SDK (`openai==0.11`) and the `text-davinci-002` model, which OpenAI has since retired. To run it today, update the API call to the current SDK and a current model.

## Team

- **Eva Vidmar**: [LinkedIn](https://www.linkedin.com/in/eva-vidmar-899b56168/)
- **Julija Stopar**: [LinkedIn](https://www.linkedin.com/in/julija-stopar/)
- **Jure Malič**: [LinkedIn](https://www.linkedin.com/in/jure-mali%C4%8D-892510202/)
