# Roam travel planner

A responsive Streamlit workspace for the existing LangGraph travel agents.

## Run

From the project directory in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

## Deploy on AWS EC2 with Docker

These steps assume an Ubuntu 24.04 EC2 instance. The Compose stack runs Streamlit
and PostgreSQL; the database is only reachable inside Docker and its data is kept
in the `postgres_data` volume. The app port is restricted to your IP because this
app does not provide user authentication and the initial setup uses plain HTTP.

1. In AWS, launch an Ubuntu 24.04 EC2 instance. Start with at least 2 vCPUs and
	4 GB RAM. Create or select an SSH key pair.
2. In the instance's security group, allow inbound SSH (TCP 22) from **My IP** and
	Streamlit (TCP 8501) from **My IP** only. Do not add an inbound PostgreSQL rule.
3. Connect from Windows PowerShell, replacing the placeholders:

	```powershell
	ssh -i .\\your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
	```

4. Install Docker and the Compose plugin on the EC2 instance:

	```bash
	sudo apt update
	sudo apt install -y docker.io docker-compose-v2 git
	sudo systemctl enable --now docker
	```

5. Get this project onto the instance. Push your changes to a private Git repository,
	then clone it on EC2 (or securely transfer the project files):

	```bash
	git clone YOUR_PRIVATE_REPOSITORY_URL roam
	cd roam
	```

6. Create the deployment environment file from the placeholder template:

	```bash
	cp .env.example .env
	nano .env
	```

	Set the three provider API keys. Generate `POSTGRES_PASSWORD` as 64 random
	hexadecimal characters, for example with `openssl rand -hex 32`. Hex is URL-safe
	in the app's PostgreSQL URL. Do not paste keys into source code, README files,
	shell command arguments, or Git. Save and close the editor.
7. Check the Compose configuration and build/start the app and database:

	```bash
	docker compose config -q
	docker compose up -d --build
	docker compose ps
	```

8. From your computer, open `http://YOUR_EC2_PUBLIC_IP:8501`. If it does not load,
	inspect app logs with `docker compose logs --tail=100 app` and confirm the EC2
	security group allows TCP 8501 from your current public IP.
9. To deploy later code changes, update the checkout and rebuild:

	```bash
	git pull
	docker compose up -d --build
	```

10. Back up PostgreSQL before replacing or removing the instance. `docker compose down`
	 keeps the named database volume. **Do not use `docker compose down -v`** unless
	 you intentionally want to delete saved checkpoints.

The initial HTTP deployment is appropriate only for restricted testing. Before
opening it to other users or the public, put it behind HTTPS (for example, Nginx
with Let's Encrypt or an AWS load balancer) and add authentication. Never expose
PostgreSQL's port to the internet. For production data durability, use managed
PostgreSQL (such as RDS) with TLS and backups; set `POSTGRES_URL` in the app's
Compose environment to that managed database instead of the bundled `db` service.

Keep `GROQ_API_KEY`, `POSTGRES_URL`, `AVIATION_STACK_API_KEY`, and
`TAVILY_API_KEY` in your local `.env`. Do not share or commit that file.
URL-encode special characters in the PostgreSQL URL password.

The database must be reachable and allow checkpoint migrations. Each trip uses
its own database connection and thread ID. Recent trips are retained for the
current browser session (up to 10); they are not a cross-session saved-trip library.

The interface includes trip preferences, agent progress, flight/train/bus research,
result tabs, recent trips, Markdown downloads, responsive layouts, and reduced-motion
support. Trip generation runs in a background worker, so changing the dark-mode switch
does not cancel a request. Destination photos and fonts require internet access. API
calls may consume provider credits.

The current flight tool returns an unfiltered schedule feed, not destination-specific
availability. The interface labels this limitation; confirm flights and prices before
booking. Hotel and itinerary output comes from the configured search and AI providers.

The original CLI remains available with `py .\main.py`.

## Backend behavior

Flight, hotel, train, and bus research run concurrently. Itinerary generation waits
for all four results, then the final overview is generated. `llm_calls` counts actual
model requests (two per successful trip), not research-tool calls. Train and bus
results come from search research; confirm routes and schedules with the operator.

The Groq client is created on first use and reused. Set `GROQ_MODEL` in `.env` to
override the default `openai/gpt-oss-120b`. Model requests have a 60-second timeout
with up to two retries; flight and hotel requests have 20-second timeouts. These
are per-request limits, not a deadline for the entire trip. Flight, hotel, train,
and bus research each have a 20-second provider timeout. CLI connections close on
completion or failure, and the CLI prints only the final response.

Run the backend regression tests without API calls or database writes:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```