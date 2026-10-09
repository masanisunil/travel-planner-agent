# Roam travel planner

A responsive Streamlit workspace for the existing LangGraph travel agents.

## Run

From the project directory in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

## Deploy on AWS EC2 with Docker

These steps assume an Ubuntu 24.04 EC2 instance and use a no-signup `sslip.io`
hostname with Caddy-provisioned HTTPS. A hostname such as
`44.202.146.158.sslip.io` resolves to the IP embedded in its name. Compose keeps
Streamlit and PostgreSQL private inside Docker and persists database data and HTTPS
certificates in named volumes. The app has no sign-in, so initially restrict HTTPS
access to your IP. Saved trips are shared with anyone who can access the app; the
`roam_saved_trips` table is created automatically in the configured PostgreSQL database.

1. In AWS, launch an Ubuntu 24.04 EC2 instance. Start with at least 2 vCPUs and
	4 GB RAM. Create or select an SSH key pair.
2. In the instance's security group, allow inbound SSH (TCP 22) from **My IP**,
	HTTP (TCP 80) from anywhere for certificate issuance and redirects, and HTTPS
	(TCP 443) from **My IP**. Do not open ports 8501 or 5432 to the internet.
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

	Set `APP_DOMAIN` to `YOUR_EC2_PUBLIC_IP.sslip.io`, replacing the placeholder
	with the instance's public IPv4 address (for example,
	`44.202.146.158.sslip.io`), plus the three provider API keys and a strong
	`POSTGRES_PASSWORD`. The app
	URL-encodes the database credentials, so passwords containing characters such
	as `@` work. Keep this password the same as the one used when the database volume
	was first initialized. Do not paste keys into source code, README files, shell
	command arguments, or Git. Save and close the editor.
7. Check the Compose configuration and build/start the app and database:

	```bash
	docker compose config -q
	docker compose up -d --build
	docker compose ps
	```

8. From your computer, open `https://YOUR_EC2_PUBLIC_IP.sslip.io`, replacing the
	placeholder with the public IPv4 address. On the first start, Caddy needs
	that hostname to resolve to this instance and inbound
	ports 80 and 443 to be reachable while it obtains its free TLS certificate.
	Check `docker compose logs --tail=100 proxy` if HTTPS does not come up.
	Streamlit is no longer published on port 8501.
9. To deploy later code changes, update the checkout and rebuild:

	```bash
	git pull
	docker compose up -d --build
	```

10. Back up PostgreSQL before replacing or removing the instance. `docker compose down`
	keeps the database and Caddy certificate volumes. **Do not use `docker compose
	down -v`** unless you intentionally want to delete saved checkpoints and certificates.

`sslip.io` requires no account or DNS record; its shared DNS service maps the
IP-address hostname to your instance, and Caddy obtains and renews its HTTPS
certificate automatically. This is convenient for testing, but it is a shared
third-party DNS service and not a permanent domain you own. If you prefer a named
free dynamic-DNS hostname, providers such as Dynu or No-IP have free tiers subject
to their account and renewal policies; set `APP_DOMAIN` to the hostname they issue.
If the EC2 public IP changes, the `sslip.io` hostname changes too; update `APP_DOMAIN`
and redeploy, or use a stable address. Do not expose the unauthenticated app publicly:
before allowing HTTPS from anywhere, add authentication. Never expose PostgreSQL's
port to the internet.
For production data durability, use managed
PostgreSQL (such as RDS) with TLS and backups; set `POSTGRES_EXTERNAL_URL` in the
EC2 `.env` to that managed database's URL. The app URL-encodes credentials supplied
as separate variables; credentials embedded in an external URL must already be
percent-encoded. Never put an external database password directly in shell commands.

Keep `GROQ_API_KEY`, `POSTGRES_URL`, `AVIATION_STACK_API_KEY`, and
`TAVILY_API_KEY` in your local `.env`. Do not share or commit that file. The Docker
deployment passes PostgreSQL host, database, user, and password separately, then
constructs an encoded connection URL inside the app.

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