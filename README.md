## Goal
The goal of this project is to combat the fragmentation between teams, groups and services in openSUSE. 

It seems to us that openUSE has many niche places that don't talk to each other that much, let alone report their activities to hubs accessible to outsiders or potentially interested contributors.

Also, events and activities are not always visible and more often than not, people would find out about a community event or an outage when it's too late.

We suspect that this kind of fragmentation and opacity makes it more difficult than necessary for new users to onboard the openSUSE Project and for users to enjoy it as much as it deserves.

Our hope is that in so doing we will also help strengthen the bounds between people, teams and communities.

## Features
- - [ ] => not implemented
- [...] => work in progress
- - [x] => implemented

### Middlewares
_Cross-platform (Matrix, Telegram) moderation_ (depends on: https://github.com/openSUSE/defrag-api/projects/2#card-64817715)
- - [ ] implement CAPTCHA (e.g. with emojis)
- - [ ] (partially implemented in [openGM](https://github.com/KaratekHD/Nemesis)) implement moderation tools (globally)
- - [ ] implement roles & badges for users (globally)

### Broadcast (push-based)
- - [ ] send service alerts
- - [ ] send community announcements
- - [ ] probe and list external services for status (unknown issue | undergoing maintenance | ups and downs | all good
### On-demand (poll-based)
- - [ ] probe and list external services for status (unknown issue | undergoing maintenance | ups and downs | all good
- list recent news / events / contribution opportunities:
    - [x] Reddit
    - [x] Twitter
- - [ ] search forum posts
- - [ ] search wiki
- [...] search bugs on bugzilla
- - [x] search openSUSE documentation
- - [ ] search Factory + Pre-Factory packages with zypper + opi
- - [ ] search for Progress / Pagure
- - [ ] search for people/activities/events

## How to contribute?
1. Set up your environment.
2. Think about what you want to change or what feature you want to add. Optionnally, talk to us about it at https://t.me/openSUSE_defrag. Ask as many questions as you need.
3. Fork & clone the repository.
4. Open an Issue where where you:
    - describe the goal of the change / new feature
    - provide an example of a typical use-case
    - request specific changes to the current code to support your feature, if you think that your feature justify making these changes and if you need such changes

Even though this is not required, in my experience working in peers (2 people working together on different parts of the same thing) works well. This can spare you a lot of time if the other person is more familiar with the code base. The better your Issue, the more likely someone will be willing to work with you.

__Important to keep in mind__:

1. We are building an _async_ server-side application/service. Make sure you don't write any code performing I/O bound computation that is *not* async. We provide the typical `loop.run_in_executor(None, ...)` trick to support sync libraries. 
2. If your Pull Request introduces a new function, it must feature a new unittest using `pytest` for it, unless your function is consumed by another function which is introduced in the same Pull Request and which does have a corresponding unittest. (Later we will need to have 1 unittest for each function though.)
3. Try to squash your commits on your Pull Requests to avoid noise.

## Set up your environment
- a virtual environment, such as `pipenv`, `virtualenv`, `venv`, etc. See [this page](https://towardsdatascience.com/comparing-python-virtual-environment-tools-9a6543643a44) for ideas.
- a Python 3.8 interpreter run from the CPython runtime (the default one)
- a static type checker such as [pyright](https://github.com/microsoft/pyright) (We are using it through [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance) and [coc-pyright](https://github.com/fannheyward/coc-pyright)).
