from datetime import date
from uuid import uuid4

from dotenv import load_dotenv
import streamlit as st
from saved_trips import delete_trip, get_trip, list_trips, rename_trip, save_trip
from trip_jobs import TripJobManager


st.set_page_config(page_title="Roam | Travel planner", page_icon=":material/explore:", layout="wide")
load_dotenv()

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

theme_colors = (
    {
        "ink": "#E8F1ED",
        "accent": "#6EE7B7",
        "muted": "#A6B9B0",
        "border": "#30433C",
        "surface": "#172329",
        "top": "#142923",
        "bottom": "#0D1519",
        "shadow": "#00000055",
        "button": "#167763",
        "logo_bg": "#6EE7B7",
        "logo_fg": "#0D342A",
    }
    if st.session_state.dark_mode
    else {
        "ink": "#202b29",
        "accent": "#16685b",
        "muted": "#687772",
        "border": "#dce3de",
        "surface": "#ffffff",
        "top": "#f0f5f2",
        "bottom": "#fbfcfa",
        "shadow": "#202b2910",
        "button": "#16685b",
        "logo_bg": "#D8EFE7",
        "logo_fg": "#16685b",
    }
)
theme_variables = ";".join(
    f"--roam-{name.replace('_', '-') }:{value}" for name, value in theme_colors.items()
)
color_scheme = "dark" if st.session_state.dark_mode else "light"

st.html(f"""
<style>
:root {{ {theme_variables}; color-scheme:{color_scheme}; }}
.stApp, [data-testid="stAppViewContainer"] {{
    background-color:var(--roam-bottom); color:var(--roam-ink); color-scheme:{color_scheme};
}}
[data-testid="stAppViewContainer"] {{
    background-image:linear-gradient(180deg,var(--roam-top) 0,var(--roam-bottom) 440px);
}}
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p, .stCaption, label {{ color:var(--roam-ink); }}
input, textarea, [data-baseweb="select"] > div,
[data-testid="stDateInput"] input, [role="listbox"], [role="option"] {{
    background-color:var(--roam-surface); color:var(--roam-ink); border-color:var(--roam-border);
}}
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputContainer"],
[data-testid="stSelectbox"] [role="combobox"],
[data-testid="stMultiSelect"] [role="combobox"],
[data-testid="stSelectbox"] [role="group"],
[data-testid="stMultiSelect"] [role="group"] {{
    background-color:var(--roam-surface) !important;
    color:var(--roam-ink) !important;
    border-color:var(--roam-border) !important;
}}
[data-testid="stTextInputField"], [data-testid="stNumberInputField"],
[data-testid="stSelectbox"] input, [data-testid="stMultiSelect"] input,
[data-testid="stNumberInputStepDown"], [data-testid="stNumberInputStepUp"] {{
    color:var(--roam-ink) !important;
    caret-color:var(--roam-accent);
}}
[data-testid="stMultiSelect"] [data-baseweb="tag"] {{
    background-color:var(--roam-button); color:#fff;
}}
[data-testid="stForm"] {{ border-color:var(--roam-border); }}
.st-key-roam_topbar {{ border-bottom:1px solid var(--roam-border); padding-bottom:.6rem; margin-bottom:1.25rem; }}
.st-key-trip_composer {{ border-color:var(--roam-border); }}
.st-key-destination_grid [data-testid="stVerticalBlockBorderWrapper"] {{
    background:var(--roam-surface); border-color:var(--roam-border);
}}
.roam-empty {{ border-color:var(--roam-border); }}
.roam-empty h3 {{ color:var(--roam-ink); }}
.roam-empty p, .roam-footer, .roam-header small {{ color:var(--roam-muted); }}
.roam-brand {{ color:var(--roam-accent); display:inline-flex; align-items:center; gap:7px;
    font-family:Manrope,sans-serif; font-size:28px; line-height:1; font-weight:800;
    letter-spacing:0; white-space:nowrap; }}
.roam-brand .roam-period {{ color:var(--roam-ink); }}
.roam-brand svg {{ width:27px; height:27px; flex:none; display:block; }}
.stButton button[kind="primary"], .stFormSubmitButton button {{
    background:var(--roam-button); color:#fff; border-color:var(--roam-button);
}}
.stButton button[kind="secondary"], .stDownloadButton button {{
    background:var(--roam-surface); color:var(--roam-ink); border-color:var(--roam-border);
}}
[data-testid="stTabs"] button {{ color:var(--roam-ink); }}
[data-testid="stExpander"] details {{
    background:var(--roam-surface) !important;
    border:1px solid var(--roam-border) !important;
    border-radius:10px !important;
}}
[data-testid="stExpander"] details > summary,
[data-testid="stExpander"] details > summary:hover {{
    background:var(--roam-surface) !important;
    color:var(--roam-ink) !important;
}}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary svg,
[data-testid="stProgress"] p {{ color:var(--roam-ink) !important; }}
[data-testid="stExpander"] summary svg {{ fill:var(--roam-ink) !important; }}
[data-testid="stExpander"] details[open] > summary {{
    border-bottom:1px solid var(--roam-border) !important;
}}
[data-testid="stProgress"] [role="progressbar"] {{ background-color:var(--roam-border); }}
[data-testid="stProgress"] [role="progressbar"] > div {{ background-color:var(--roam-button); }}
</style>
""")

DESTINATIONS = [
    ("Bali", "Indonesia", "Island days & quiet escapes", "photo-1537996194471-e657df975ab4"),
    ("Jaipur", "India", "Palaces, markets & pink streets", "photo-1599661046827-dacff0c0f09a"),
    ("Kyoto", "Japan", "Temple trails & timeless corners", "photo-1493976040374-85c8e12f0c0e"),
]
STEPS = {
    "flight_agent": "Flight research complete",
    "hotel_agent": "Places to stay found",
    "train_agent": "Train routes researched",
    "bus_agent": "Bus routes researched",
    "itineray_agent": "Your itinerary is taking shape",
    "final_agent": "The finishing touches are ready",
}

st.html("""
<style>
.stMainBlockContainer { max-width: 1400px; padding-top: 1.8rem; padding-bottom: 3rem; }
h1, h2, h3, p, button, input, textarea { letter-spacing: 0 !important; }
header[data-testid="stHeader"] { background: transparent; }
.roam-header { display:flex; align-items:center; justify-content:space-between; gap:1rem;
    padding:0 0 1.25rem; border-bottom:1px solid #dce3de; margin-bottom:1.25rem; }
.roam-brand { font-family:Manrope,sans-serif; font-size:27px; font-weight:800; }
.roam-header small { font-size:12px; }
.roam-hero { position:relative; min-height:220px; display:flex; align-items:center;
    background: #246f63 url('https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=1800&q=85') center 55%/cover;
    margin-bottom:1.8rem; overflow:hidden; animation:roam-reveal .65s ease both; }
.roam-hero::before { content:''; position:absolute; inset:0;
    background:linear-gradient(90deg,rgba(13,36,29,.7),rgba(13,36,29,.08)); }
.roam-hero-content { position:relative; color:white; padding:2rem 2.5rem; max-width:640px; }
.roam-hero h1 { color:white; font-size:46px; line-height:1.1; margin:0 0 .6rem; padding:0; }
.roam-hero p { color:#f1f6f3; font-size:16px; margin:0; }
.roam-eyebrow { font-size:11px; text-transform:uppercase; font-weight:700; margin-bottom:.7rem; }
.st-key-trip_composer { padding-right:1.5rem; border-right:1px solid var(--roam-border); }
.st-key-workspace { animation:roam-reveal .75s .1s ease both; }
.st-key-trip_composer [data-testid="stForm"] { padding:0; }
.stButton button, .stFormSubmitButton button { transition:background .2s, transform .2s, box-shadow .2s; }
.stButton button:hover, .stFormSubmitButton button:hover { transform:translateY(-2px); box-shadow:0 4px 12px var(--roam-shadow); }
.st-key-destination_grid [data-testid="stVerticalBlockBorderWrapper"] { transition:transform .25s, box-shadow .25s; }
.st-key-destination_grid [data-testid="stVerticalBlockBorderWrapper"]:hover { transform:translateY(-4px); box-shadow:0 10px 24px var(--roam-shadow); }
.st-key-destination_grid img { width:100%; aspect-ratio:4/3; object-fit:cover; border-radius:4px; }
.st-key-destination_grid [data-testid="stColumn"] { animation:roam-reveal .6s ease both; }
.st-key-destination_grid [data-testid="stColumn"]:nth-child(2) { animation-delay:.1s; }
.st-key-destination_grid [data-testid="stColumn"]:nth-child(3) { animation-delay:.2s; }
.roam-empty { padding:1.5rem 0 1.2rem; border-top:1px solid var(--roam-border); margin-top:1.5rem; }
.roam-empty h3 { font-size:18px; margin:0 0 .35rem; }
.roam-empty p { font-size:14px; margin:0; }
.roam-footer { display:flex; justify-content:space-between; flex-wrap:wrap; gap:.6rem;
    border-top:1px solid var(--roam-border); padding-top:1.2rem; margin-top:2rem; font-size:12px; }
@keyframes roam-reveal { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
@media(max-width:900px) { .stMainBlockContainer { padding:1.3rem 1.2rem 2rem; }
    .roam-hero-content { padding:1.7rem; } .roam-hero h1 { font-size:38px; } }
@media(max-width:640px) { .roam-hero { min-height:190px; margin-bottom:1.2rem; }
    .roam-hero h1 { font-size:32px; } .roam-hero p { font-size:14px; }
    .st-key-trip_composer { padding-right:0; border-right:0; border-bottom:1px solid var(--roam-border); padding-bottom:1.4rem; }
    .roam-header small { max-width:110px; text-align:right; } }
@media(prefers-reduced-motion:reduce) { *, *::before, *::after { animation:none !important; transition:none !important; } }
</style>
""")


def choose_destination(destination):
    st.session_state.destination = destination


def generate_trip(query, origin_city, destination_city, on_progress):
    import psycopg
    from langchain_core.messages import HumanMessage
    from langgraph.checkpoint.postgres import PostgresSaver
    from main import get_database_url, graph

    database_url = get_database_url()
    if not database_url:
        raise ValueError("Missing database configuration")
    config = {"configurable": {"thread_id": str(uuid4())}}
    initial = {
        "messages": [HumanMessage(content=query)], "user_query": query,
        "origin_city": origin_city, "destination_city": destination_city,
        "flight_results": "", "train_results": "", "bus_results": "",
        "hotel_results": "", "itinerary": "", "llm_calls": 0,
    }
    with psycopg.connect(database_url, autocommit=True, connect_timeout=10) as connection:
        checkpointer = PostgresSaver(connection)
        checkpointer.setup()
        travel_app = graph.compile(checkpointer=checkpointer)
        completed = 0
        for update in travel_app.stream(initial, config=config, stream_mode="updates"):
            for node in update:
                completed += 1
                label = STEPS.get(node, "Planning your trip")
                on_progress(label, completed, len(STEPS))
        return travel_app.get_state(config).values


def trip_database_url():
    from main import get_database_url

    return get_database_url()


@st.cache_resource
def get_trip_job_manager():
    return TripJobManager(max_workers=4)


@st.fragment(run_every="1s")
def show_trip_job(job_id):
    job = get_trip_job_manager().snapshot(job_id)
    if job is None:
        st.session_state.generation_job_id = None
        st.session_state.generation_error = "The trip task expired. Please start again."
        st.rerun()
    if job["done"]:
        st.session_state.generation_job_id = None
        if job["error"]:
            st.session_state.generation_error = (
                "Trip planning could not finish. Check your API keys, database connection, "
                "and provider limits, then try again. Your previous trips are still available."
            )
        else:
            details = job["trip_details"]
            trip = {**details, "result": job["result"]}
            try:
                save_trip(trip_database_url(), trip)
                st.session_state.history_error = None
            except Exception:
                st.session_state.history_error = (
                    "Your itinerary is ready, but it could not be saved to trip history."
                )
            st.session_state.active_trip = trip
            st.session_state.generation_error = None
        get_trip_job_manager().discard(job_id)
        st.rerun()
    with st.expander(
        f"Finding your next escape... ({job['completed']}/{job['total']} steps)",
        expanded=True,
        icon=":material/travel_explore:",
    ):
        st.progress(min(job["completed"] / max(job["total"], 1), 1.0))
        if job["steps"]:
            for step in job["steps"]:
                st.markdown(f":green[:material/check_circle:] {step}")
        if job["completed"] < job["total"]:
            pending_steps = [step for step in STEPS.values() if step not in job["steps"]]
            st.caption(f"Up next: {pending_steps[0]}" if pending_steps else "Finalizing your itinerary...")
        elif not job["steps"]:
            st.caption("Preparing your research...")


if "destination" not in st.session_state:
    st.session_state.destination = "Bengaluru"
if "active_trip" not in st.session_state:
    st.session_state.active_trip = None
if "generation_job_id" not in st.session_state:
    st.session_state.generation_job_id = None
if "generation_error" not in st.session_state:
    st.session_state.generation_error = None
if "history_error" not in st.session_state:
    st.session_state.history_error = None
if "delete_trip_confirmation" not in st.session_state:
    st.session_state.delete_trip_confirmation = None

try:
    database_url = trip_database_url()
    saved_trips = list_trips(database_url)
    history_load_error = None
except Exception:
    database_url = None
    saved_trips = []
    history_load_error = "Saved trip history is unavailable. Check the database connection."

with st.container(key="roam_topbar"):
    brand, theme_control, tagline = st.columns([1, 0.8, 1], vertical_alignment="center")
    with brand:
                st.html("""
                <div class="roam-brand" aria-label="Roam travel">
                      <span>Roam<span class="roam-period">.</span></span>
                    <svg viewBox="0 0 32 32" role="img" aria-label="Backpacker walking">
                        <circle cx="16" cy="16" r="15" fill="var(--roam-logo-bg)"/>
                        <g fill="none" stroke="var(--roam-logo-fg)" stroke-width="2.1"
                             stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="13" cy="8.5" r="2.3" fill="var(--roam-logo-fg)" stroke="none"/>
                            <path d="m12.5 12 3.2 4.1 3.8 1.2M13 12l-3.3 4.2-2 .8M12.8 14.2l3.2 2.2-1.3 4.2M13 15l-3.1 4.1-3.4 1.7"/>
                            <path d="M18 11.7h3.1c1.2 0 2 .9 2 2v4.2c0 1.1-.8 1.9-1.9 1.9h-2.1"/>
                            <path d="M18 12.5v5.7"/>
                        </g>
                    </svg>
                </div>
                """)
    with theme_control:
        st.toggle("Dark mode", key="dark_mode")
    with tagline:
        st.caption("A world of possibilities")

st.html("""
<section class="roam-hero"><div class="roam-hero-content">
<div class="roam-eyebrow">The journey starts here</div>
<h1>Roam. Your next escape.</h1><p>Good days. New places. A trip that feels like you.</p>
</div></section>
""")

composer, workspace = st.columns([1, 2.15], gap="large")
with composer, st.container(key="trip_composer"):
    st.subheader("Make it your trip")
    st.caption("A few details. A world to discover.")
    with st.form("trip_form", border=False):
        destination = st.text_input("Where to?", key="destination", placeholder="City or destination")
        origin = st.text_input("Travelling from", placeholder="Your departure city (optional)")
        start_date = st.date_input("Departure date", value=date.today(), min_value=date.today())
        duration = st.number_input("Days away", min_value=1, max_value=30, value=3, step=1)
        budget = st.selectbox("Travel budget", ["Balanced", "Budget-friendly", "Luxury"])
        interests = st.multiselect("Your kind of trip", ["Food", "Culture", "Nature", "Adventure", "Shopping", "Relaxation"], default=["Food", "Culture"])
        with st.expander("A little more about your trip", icon=":material/tune:"):
            travellers = st.number_input("Travellers", min_value=1, max_value=20, value=1)
            notes = st.text_area("Special requests", placeholder="Dietary needs, accessibility, places you love...")
        submitted = st.form_submit_button("Plan my escape", icon=":material/arrow_forward:", type="primary", width="stretch")
    st.space("small")
    with st.expander(f"Saved trips ({len(saved_trips)})", expanded=False, icon=":material/history:"):
        st.caption("Saved trips are shared with anyone who can access this app.")
        if history_load_error:
            st.warning(history_load_error)
        elif saved_trips:
            trip_options = {trip["id"]: trip for trip in saved_trips}
            selected_trip_id = st.selectbox(
                "Choose a saved trip",
                options=list(trip_options),
                format_func=lambda trip_id: (
                    f"{trip_options[trip_id]['title']} · "
                    f"{trip_options[trip_id]['duration']} days"
                ),
                key="saved_trip_selection",
                label_visibility="collapsed",
            )
            selected_trip = trip_options[selected_trip_id]
            with st.container(horizontal=True):
                if st.button("Open", key="open_saved_trip", icon=":material/open_in_new:"):
                    st.session_state.active_trip = get_trip(database_url, selected_trip_id)
                    st.rerun()
                with st.popover("Manage", icon=":material/more_vert:"):
                    with st.form(f"rename_trip_{selected_trip_id}"):
                        new_title = st.text_input("Trip name", value=selected_trip["title"])
                        if st.form_submit_button("Save name", icon=":material/edit:"):
                            if not new_title.strip():
                                st.error("Enter a name for this trip.")
                            elif rename_trip(database_url, selected_trip_id, new_title):
                                active_trip = st.session_state.active_trip
                                if active_trip and active_trip["id"] == selected_trip_id:
                                    active_trip["title"] = new_title.strip()
                                st.rerun()
                            else:
                                st.error("This saved trip no longer exists.")
                    if st.button(
                        "Delete trip",
                        key=f"request_delete_{selected_trip_id}",
                        icon=":material/delete:",
                    ):
                        st.session_state.delete_trip_confirmation = selected_trip_id
                        st.rerun()
            if st.session_state.delete_trip_confirmation == selected_trip_id:
                st.warning(f"Delete '{selected_trip['title']}' permanently?")
                confirm_column, cancel_column = st.columns(2)
                with confirm_column:
                    if st.button("Confirm delete", key="confirm_delete_trip", type="primary"):
                        delete_trip(database_url, selected_trip_id)
                        if (
                            st.session_state.active_trip
                            and st.session_state.active_trip["id"] == selected_trip_id
                        ):
                            st.session_state.active_trip = None
                        st.session_state.delete_trip_confirmation = None
                        st.rerun()
                with cancel_column:
                    if st.button("Cancel", key="cancel_delete_trip"):
                        st.session_state.delete_trip_confirmation = None
                        st.rerun()
        else:
            st.caption("Your completed itineraries will appear here.")

with workspace, st.container(key="workspace"):
    if submitted:
        if not destination.strip():
            st.error("Choose a destination before starting your trip.")
        else:
            query = (
                f"Plan a {duration}-day trip to {destination.strip()} starting {start_date.isoformat()} "
                f"for {travellers} traveller(s). Budget: {budget}. "
                f"Departure city: {origin.strip() or 'not provided'}. "
                f"Interests: {', '.join(interests) or 'a balanced mix'}. Requests: {notes.strip() or 'none'}. "
                "Give a practical day-by-day itinerary in Markdown with morning, afternoon and evening plans. "
                "Compare flight, train, and bus options using the supplied research. Include useful hotel links. "
                "Do not invent prices, bookings, or schedules. Flight results are an unfiltered feed: do not "
                "recommend unrelated routes or claim destination-specific flight availability. Label any "
                "unverified transit schedule clearly and link to its research source."
            )
            if st.session_state.generation_job_id:
                st.warning("A trip is already being planned. You can switch themes while it runs.")
            else:
                trip_id = str(uuid4())
                trip_details = {
                    "id": trip_id,
                    "destination": destination.strip(),
                    "duration": duration,
                    "date": start_date.isoformat(),
                    "budget": budget,
                }
                st.session_state.generation_error = None
                st.session_state.generation_job_id = trip_id
                get_trip_job_manager().start(
                    trip_id,
                    lambda on_progress: generate_trip(
                        query, origin.strip(), destination.strip(), on_progress
                    ),
                    trip_details,
                    len(STEPS),
                )

    if st.session_state.generation_error:
        st.error(st.session_state.generation_error)
    if st.session_state.history_error:
        st.warning(st.session_state.history_error)
    if st.session_state.generation_job_id:
        show_trip_job(st.session_state.generation_job_id)

    trip = st.session_state.active_trip
    if trip:
        result = trip["result"]
        st.caption("YOUR NEXT CHAPTER")
        st.header(trip.get("title") or trip["destination"])
        st.caption(f"{trip['destination']} / {trip['duration']} days / {trip['date']} / {trip['budget']}")
        itinerary_tab, stays_tab, transport_tab, overview_tab = st.tabs(["Itinerary", "Places to stay", "Transport options", "Trip overview"])
        with itinerary_tab:
            st.markdown(result.get("itinerary") or "No itinerary was returned.")
        with stays_tab:
            st.markdown(result.get("hotel_results") or "No places to stay were returned.")
        with transport_tab:
            flight_tab, train_tab, bus_tab = st.tabs(["Flights", "Trains", "Buses"])
            with flight_tab:
                st.warning("Flight data is an unfiltered schedule feed, not a route search. Confirm routes and availability directly with the airline.", icon=":material/info:")
                st.text(result.get("flight_results") or "No flight data was returned.")
            with train_tab:
                st.caption("Research only. Confirm routes and timetables with the official railway operator before travel.")
                st.markdown(result.get("train_results") or "No train research was returned.")
            with bus_tab:
                st.caption("Research only. Confirm routes and timetables with the official bus operator before travel.")
                st.markdown(result.get("bus_results") or "No bus research was returned.")
        with overview_tab:
            messages = result.get("messages", [])
            final = result.get("overview") or (
                messages[-1].content if messages else "No trip overview was returned."
            )
            st.markdown(final if isinstance(final, str) else str(final))
        document = (
            f"# {trip['destination']}\n\n{trip['duration']} days | {trip['date']}\n\n"
            f"{result.get('itinerary', '')}\n\n## Flights\n\n{result.get('flight_results', '')}"
            f"\n\n## Trains\n\n{result.get('train_results', '')}"
            f"\n\n## Buses\n\n{result.get('bus_results', '')}"
            f"\n\n## Places to stay\n\n{result.get('hotel_results', '')}"
        )
        with st.container(horizontal=True):
            st.download_button("Download itinerary", data=document, file_name="roam-itinerary.md", mime="text/markdown", icon=":material/download:")
            if st.button("New trip", icon=":material/add:"):
                st.session_state.active_trip = None
                st.rerun()
    else:
        st.caption("A LITTLE INSPIRATION")
        st.header("Somewhere worth going")
        st.caption("A change of scenery is always a good idea.")
        with st.container(key="destination_grid"):
            columns = st.columns(3, gap="small")
            for column, (city, country, description, image) in zip(columns, DESTINATIONS):
                with column, st.container(border=True):
                    st.image(f"https://images.unsplash.com/{image}?auto=format&fit=crop&w=600&q=80", alt=f"Travel scenery in {city}", width="stretch")
                    st.caption(country.upper())
                    st.subheader(city)
                    st.caption(description)
                    st.button("Explore", key=f"explore_{city}", icon=":material/north_east:", on_click=choose_destination, args=(city,), width="stretch")
        st.html("""<div class="roam-empty"><h3>Your itinerary belongs here.</h3>
        <p>Leave room for the unexpected. The best stories often happen along the way.</p></div>""")

st.html('<div class="roam-footer"><span>roam. / Go somewhere good.</span><span>Availability and prices should be confirmed before booking.</span></div>')