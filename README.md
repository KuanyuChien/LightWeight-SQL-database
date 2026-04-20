# WEEK 12
## Proposal
For my final project, I am going to build a lightweight in-memory SQL database from scratch. The database will support basic relational features like create table, insert, and simple select ... where queries. The main thing I want to show is that the system can take SQL commands as input, parse them correctly, store the data in memory, and return the right results. I also want to show off the different parts behind the scenes, such as the tokenizer, the parser, the internal data storage, and the query execution logic. Overall, I think this is a cool project because it feels more like building a real system than just making a simple app, and I believe it would help me imrove my inderstanding for the database system which is a class I am also taking.

To make this project, I plan to use an AI coding agent in a repeated loop where it keeps improving the database based on feedback. The agent will work on one part at a time, like parsing, storage, or query execution, then run tests right away to see what is working and what is failing. The main feedback will come from sqllogictest, which has lots of SQL test cases with expected outputs. I want the agent to use failed tests, wrong query results, parser errors, and crashes as signals for what to fix next. So the process will be: generate code, run tests, look at the failures, improve the code, and repeat. I think this is a good use of AI because the project has a very clear way to measure progress, and I can show that the system is getting better by passing more tests over time.tests it passes.

# WEEK 13
**What's working so far on your project? What are your concrete plans for the next week?**

Trying to build the basics of a SQL database, improve efficiency, and increase the number of tests that pass.

**What are the smartest and dumbest thing your agent loop did this week? If you're using Amp, link to the relevant threads. What did you change to stop the agent from doing that dumb thing again?**

https://ampcode.com/threads/T-019d74e6-ef23-73fe-9392-5705a81a93a3#message-119-block-3

I stopped the loop because I noticed the tests were taking longer and longer to finish, and sometimes they would just get stuck. From what I can tell, the test runner is doing too much work in the wrong order.
The main issue seems to be how joins are being handled. Right now, the code appears to use the naive approach for SQL joins: it takes every row from table 1 and pairs it with every row from table 2, then takes all of those combinations and pairs them with every row from table 3, and keeps repeating that before applying the where conditions. This basically creates a cartesian product, which grows extremely fast and makes the runtime much worse as more tables are involved.

To improve this, I want the agent to pay more attention to efficiency and consider different approaches when performance starts getting bad, especially since this project may need to handle large amounts of data. Instead of building huge intermediate combinations first, it should try to reduce the search space earlier and think more carefully about join order and other possible optimizations. In addition, I think add a timer maybe helpful and ask agent to not run the entire test suit at once.

Also, I realized I never asked the agent to generate a bug report, so I am going to add a BUG_REPORT.md file as part of the workflow as well.

## Demo Dashboard

- Rebuild the dashboard data with `python3 scripts/generate_dashboard_data.py`.
- Open [`dashboard/index.html`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/dashboard/index.html) directly in a browser for the static demo page, or serve the folder with `python3 -m http.server 8000 --directory dashboard` if you prefer a local URL.
- The dashboard is intentionally lightweight and derives its content from `TASKS.md`, `PROGRESS.md`, `BUG_REPORT.md`, `README.md`, the staged sqllogictest file list, and example SQL executed against the current engine.

# WEEK 14
vidoe link: https://youtu.be/WutdBItG5NI