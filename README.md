# **NutriPatrol 🛡️**

**A collaborative tool to monitor and improve food product data on Open Food Facts.**

NutriPatrol is a web-based application designed to help the Open Food Facts community ensure the quality and accuracy of the data in the world's largest open database of food products. It allows users to easily patrol recent changes, spot inaccuracies, and contribute to making the food supply chain more transparent.

Production: <https://nutripatrol.openfoodfacts.org>
Pre-production: <https://nutripatrol.openfoodfacts.net>

## This is the backend
- The frontend is located at https://github.com/openfoodfacts/nutripatrol-frontend

## API documentation
https://nutripatrol.openfoodfacts.org/api/docs

## SDKs
- Available in the JS SDK, the Dart SDK: https://github.com/openfoodfacts/openfoodfacts-js, https://github.com/openfoodfacts/openfoodfacts-dart

## Webcomponent
- Available as a webcomponent: https://openfoodfacts.github.io/openfoodfacts-webcomponents/?path=/story/components-nutri-patrol--flag-product

## Understanding Open Food Facts' data quality infrastructure
- https://wiki.openfoodfacts.org/Category:Data_quality
- https://wiki.openfoodfacts.org/Data_quality

## **🌟 About the Project**

The goal of NutriPatrol is to gamify the process of data verification for Open Food Facts. Moderators can quickly swipe through recent reports, to act on true issues and mark them as fixed, or flag incorrect ones as not a problem. This helps maintain the integrity of the data that powers countless apps and research projects related to food, nutrition, and health.

### **Key Features:**

* **🕵️‍♀️ Patrol Recent Reports:** Quickly review and verify edits made to products.  
* **✅ Approve or Flag from many places:** Basic integration is available in the website (openfoodfacts-server), being added to openfoodfacts-explorer and the mobile app (smooth-app)  
* **📱 Mobile-Friendly:** A responsive design that works on any device.

## **🚀 Getting Started**

To get a local copy up and running, follow these simple steps.

### **Prerequisites**

- A running Docker daemon and the Compose plugin (`docker compose`). On Ubuntu,
  `sudo apt install docker.io docker-compose-v2` is enough — no Docker Hub account
  is needed, the only images pulled from Hub are `postgres` and `nginx`.
- `make`.

### **Installation**

1. Clone this repository :

```console
git clone https://github.com/openfoodfacts/nutripatrol.git
```

```console
cd nutripatrol
```

### Run with docker containers

Make docker containers

```console
make up
```

Then apply the database migrations. This step is required: nothing creates the tables
at startup, so every endpoint that touches the database fails until you run it.

```console
make migrate-db
```

The API should now be running at <http://localhost:8000>, with the interactive
documentation at <http://localhost:8000/api/docs>.

Note that <http://localhost:8000/> itself returns a 403 in a dev checkout: nginx serves
the `static/` directory there, and that directory only holds the built frontend in
production. This is expected — use `/api/docs` to check that the API is alive.

The frontend is a separate repository
([nutripatrol-frontend](https://github.com/openfoodfacts/nutripatrol-frontend)) and runs
on <http://localhost:5173>.

### Authentication for local dev

Every useful endpoint requires authentication, so this section is not optional if you
want to do anything beyond `/api/docs`.

#### To test with a global instance of Product Opener

In the .env file uncomment the AUTH_SERVER_STATIC variable.
If you want to use a local Product Opener Instance, use `http://world.openfoodfacts.localhost`

This variable is **required for local development**. Without it the API derives the
authentication server from the request host by replacing `nutripatrol` with `world`
(see `app/middleware/auth.py`). On `http://localhost:8000` there is nothing to replace,
so it ends up calling `https://localhost:8000/cgi/auth.pl` and every login fails.

Make sure it points at the same environment as `OFF_TLD` in the same file — a session
cookie taken from `openfoodfacts.org` will not match flag URLs generated for
`openfoodfacts.net`.

Then connect to your Open Food Facts profile, copy the session cookie (use developper toolbar, and find a cookie named session for openfoodfacts.org domain, copy its value)
and paste it in the body at this endpoint /api/v1/set_session_cookie (you have a form at the /api/docs URI).

#### Without an Open Food Facts moderator account

A bearer token short-circuits the authentication dependency entirely, which is the
quickest way to exercise the API locally. It is set to `local-dev-token` in the
committed dev `.env`:

```console
curl -H "Authorization: Bearer local-dev-token" \
  "http://localhost:8000/api/v1/tickets?type_=image&status=open&page=1&page_size=10"
```

## **📖 Usage**

Once the application is running, you can log in with your Open Food Facts account. The main screen will present you with cards showing recent reports. You might need to be a moderator to be able to use it.

### **How to Contribute**


## Pre-Commit

This repo uses [pre-commit](https://pre-commit.com/) to enforce code styling, etc. To use it:

```console
pre-commit run
```
## **🤝 Contributing**

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this project better, please fork the repo and create a pull request. You can also simply open an issue with the type "enhancement".


## Wikipage

- <https://wiki.openfoodfacts.org/Moderation>
- [Meeting minutes](https://docs.google.com/document/d/1B9Ci42kl_jrFt2hi3PiWW9tM9l6B1sI5kQMI9Zd6QS4/edit)

## 🎨 Design
- [![Figma](https://img.shields.io/badge/figma-%23F24E1E.svg?logo=figma&logoColor=white) Mockups & Benchmarks](https://www.figma.com/design/SRU9iQ5DIpKNa6izKEiqyo/NutriPatrol--quality-?node-id=48-36&p=f&t=Ly2rYxJgs4fcTane-0)
- Are you a designer ? [Join the design team](https://github.com/openfoodfacts/openfoodfacts-design)
## Features
- Image reporting
- List of tickets (can be images, products…)
- List of reported images (both by humans and Robotoff, our AI)
## Roadmap
### Backend
- [ ] Support frontend features (filters, displaying the reporter, displaying the uploader…)
### Frontend
- [ ] More filters to focus on the most important issues first
- [ ] Quick and easy actions to fix the errors
## Weekly meetings

We currently have no maintener for this tool. Please ping us here or on Slack if you'd like to contribute.
We have more general quality meetings every month.
- The meeting will handle Agenda items first, and if time permits, collaborative bug triage.
- We strive to timebox the core of the meeting (decision making) to 30 minutes, with an optional free discussion/live debugging afterwards.
- We take comprehensive notes in the Weekly Agenda of agenda item discussions and of decisions taken.
Please read our [Contributing Guidelines](https://github.com/openfoodfacts/nutripatrol/blob/main/CONTRIBUTING.md) for more details on our code of conduct and the process for submitting pull requests.

## **📜 License**

Distributed under the AGPL. See LICENSE for more information.

## **📬 Contact**

Open Food Facts - tech@openfoodfacts.org

Project Link: [https://github.com/openfoodfacts/nutripatrol](https://github.com/openfoodfacts/nutripatrol)

This README is a starting point. Feel free to suggest improvements!
## Contributors

<a href="https://github.com/openfoodfacts/nutripatrol-frontend/graphs/contributors">
<img alt="List of contributors to this repository" src="https://contrib.rocks/image?repo=openfoodfacts/nutripatrol-frontend" />
</a>
