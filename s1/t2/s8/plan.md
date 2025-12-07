write node js code that:
1. connects to cdp(usually port 9222)
2. shows user available tabs
3. user picks a tab or gives a url
4. code gets the html of that page and sends to LLM
5. LLMs are pre-configured by user: api key, model, base url
6. LLM figures out what could the user want to scrape from the html
7. LLM asks user if what LLM thinks works for user
8. If user rejects go to 3
9. If user accepts LLM writes code to scrape
10. Code is run, data is saved in a csv file, if user rejects go to 9
11. If user accepts go to 3

As you can see this code has parts that match perfectly with a CRUD interface(table, form):

- CDP endpoints
- LLMs
- Generated Codes
- Runs(with csv output)

I am inclined to these ideas:

- open source no code low code tools, there are tools that generate APIs from DBs, for example soul for sqlite and potgrest for postgresql.
- save data in a database or the file system, the file system allows developers, admins, and users to easily CRUD application data, workflows and configuration
- saving workflows and data separated, in this file the 11 steps are one workflow, and the CRUD interfaces are the data

write in another file how would you implement this application.