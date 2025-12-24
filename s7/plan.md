use bun js to create a scraper application, give user the maximum control and organize code as if it a CRUD of whatever resource needed.

Use pocketbase.

First you need to create data schema for scraper app, remember to give user maximum control, this is a power user, interested in seeing the internals of the application, to debug it, to see each step of the data pipeline, so no mocks, add clear and not disruptive errors(for example using messages in the web page instead of alert), error history.

Application should save history for everything user enters, configs and data. Also errors.

Application should support multiple users

Add tests inside the application without mocks, example: user can create tests, saved in db. Which user can run whenever he wants, app has run history and complete view of each step of data pipeline.

Example:
- User enters url acquire.com
- User has a button where an AI uses a CDPd browser to navigate and figure out what the user would like to extract
- App offers alternatives to extract: items of a paginated list page, or details of a show page
- User picks one or many options
- User has a button let AI know start writing code 
- AI writes code and tests that data is being extracted correctly
- AI should be able to own entire iterations until code is perfect
- User can set a schedule to extract data, and set a data sink

Remember user can see each step of the process so he can help AI in case AI does not have the right data or context to solve issues.

Let user configure as many AI models as he wants: api key, api url, model id

Let user configure as many browsers as he wants, this part I am not sure which fields it needs, in previous tests I have seen that just an URL is needed for a CDPd browser is enough. App will mostly use full headed browsers running CDP.

Let user configure as many data sinks as he wants.
Remember each thing needs to be CRUDable. Errors real. No Mocks. Full transparency to the user