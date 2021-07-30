## Goal
The goal of this project is to combat the fragmentation between teams, groups and services in openSUSE. 

It seems to us that openUSE has many niche places that don't talk to each other that much, let alone report their activities to hubs accessible to outsiders or potentially interested contributors.

Also, events and activities are not always visible and more often than not, people would find out about a community event or an outage when it's too late.

We suspect that this kind of fragmentation and opacity make it more difficult than necessary for new users to onboard the openSUSE Project and for users to enjoy it as much as it deserves.

Our hope is that in so doing we will also help strengthen the bounds between people, teams and communities.

## Features (subject to changes)
_Searching external services_
- search forum posts
- search wiki
- ~~search bugs on bugzilla~~ (quicksearch not provided by Bugzilla 4.4)
- search openSUSE documentation
- search Factory + Pre-Factory packages with zypper + opi
- search for Progress / Pagure
- search for people/activities/events

_Cross-platform moderation_ (depends on: https://github.com/KaratekHD/defrag/projects/2#card-64817715)
- implement CAPTCHA with emojis
- (partially implemented in karatekbot) implement moderation tools (globally)
- implement roles & badges for users (globally

_Brodcasting_
- send service alerts
- send community announcements

_On-demand channels_
- probe an list external services for status (unknown issue | undergoing maintenance | ups and downs | all good
- list recent news / events / contribution opportunities:
    - [x] Reddit
    - [x] Twitter