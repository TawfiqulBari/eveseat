Development Plan for an EVE Online Integrated Docker Application
Architecture Overview
This application will follow a microservices architecture deployed via Docker containers for each major component. Using Docker Compose (for development) and Kubernetes (for production) will ensure each service is isolated, scalable, and easy to maintain. The high-level design includes:
Frontend UI (React/Vue single-page app served via Nginx)
API Gateway/Server (RESTful backend service to handle client requests and aggregate data)
ESI Integration Services (background workers to fetch and sync EVE ESI data: characters, corporations, market, killmails, etc.)
Map Data Service (provides processed universe map data and route calculations to the frontend)
Database (persistent store for user accounts, characters, and cached EVE data – e.g. PostgreSQL)
Cache/Queue (Redis for caching frequently used data and for job queue broker)
Background Job Scheduler (periodic tasks for data polling, e.g. Celery Beat or cron service)
Reverse Proxy (Traefik or Nginx to route requests and handle TLS in production)
Table: Microservice Components and Technologies
Service/Container	Purpose	Technology Stack
Frontend (UI)	Interactive web UI for users	React or Vue, served via Nginx
API Server	REST API for frontend & external calls	Node.js (Express) or Python (FastAPI)
ESI Worker	Fetch EVE ESI data (characters, market)	Python Celery (Redis for queue)
Killmail Processor	Real-time killmail feed integration	Python Celery or Node worker (Redis)
Scheduler	Schedule periodic ESI polls	Celery Beat / cron (in worker container)
Database	Persistent data store	PostgreSQL (relational DB)
Cache/Message Queue	Caching, job queue broker	Redis (in-memory store)
Reverse Proxy	Routing, load balancing, TLS termination	Traefik or Nginx (Docker container)
Each service runs in its own container, enabling independent scaling. For example, the frontend is decoupled and served as static files, the API handles client requests, and dedicated worker containers handle heavy data-fetch tasks asynchronously. This separation follows best practices as seen in existing EVE tools: SeAT (an open-source EVE app) uses multiple containers (web frontend, a worker for jobs, a scheduler for tasks, a cache, and a database) orchestrated via docker-compose
eveseat.github.io
. We will adopt a similar approach to maximize modularity and maintainability.
EVE Online API Integration (ESI)
EVE Swagger Interface (ESI) will be the core of data integration. ESI provides ~195 endpoints (119 authenticated) covering virtually all game data
wiki.eveuniversity.org
. The app will consume all relevant ESI endpoints, including: character info, corporation details, killmails, market data, sovereignty, industry jobs, and more. ESI offers both public and private (authenticated) endpoints; accessing character/corporation-specific data requires SSO OAuth2 login
wiki.eveuniversity.org
. OAuth2 Authentication: We will register our application on the official EVE Developers portal (obtaining a Client ID/secret)
eveseat.github.io
. Users will securely authenticate via CCP’s Single Sign-On, granting our app access tokens for the requested scopes. We will request broad ESI scopes to cover all features (e.g. esi-characters.read_*, esi-corporations.read_*, esi-killmails.read_*, esi-markets.*, esi-industry.*, esi-location.read_location.v1, etc.). The design supports multiple characters per user: a user account can link several EVE characters by repeating the OAuth flow for each. Each character’s OAuth token (and refresh token) will be stored encrypted in the database and tied to the user’s account. This allows consolidated access while keeping character data separate. Token refreshes are handled automatically by server-side logic whenever an access token expires (using refresh tokens in background). Data Retrieval and Caching: Once authorized, background services will pull data from ESI on a schedule (respecting ESI’s cache timers and rate limits). Key ESI integration points include:
Character & Corporation Data: Basic character info, skill points, assets, wallet, contacts, etc., and corporation info like member list, roles, assets, wallet, etc. (requires director roles for corp data). ESI’s “Character” category (10 auth endpoints) and “Corporation” category (18 auth endpoints) provide these details
wiki.eveuniversity.org
wiki.eveuniversity.org
. We will store essential character/corp details in our database for quick access and cross-character aggregation (with periodic refresh). For example, when a user links a character, the app calls ESI to fetch that character’s profile, corp, skills, etc., and saves them.
Killmails: The app will integrate killmail data extensively. ESI’s killmail endpoints allow fetching a character’s recent killmail IDs and details of specific killmails
wiki.eveuniversity.org
. For personal or corp kill feeds, we will use these authenticated endpoints. However, to show global kill activity, we will integrate with zKillboard. zKillboard provides a push feed (RedisQ or WebSocket) that delivers killmails in real-time, and APIs for fetching historical killmails and statistics
github.com
. Our killmail processing service will subscribe to zKill’s feed (ensuring we get all kill events as they happen) and log relevant data (e.g. system, time, ships destroyed) for the map’s “recent kills” overlay and a real-time feed in the UI. This hybrid approach ensures comprehensive coverage: personal kills from ESI (even if not public on zKill) and all public kills via zKillboard. We will also utilize zKill’s stats API to retrieve historical or aggregate data if needed (e.g. top kills, kill counts)
github.com
.
Market Data: The app will retrieve market information to support price checks, trading dashboards, etc. ESI offers market endpoints for item prices, market orders by region, and market history
wiki.eveuniversity.org
. We will integrate the public market endpoints (e.g. region market orders, historical prices) and possibly supplement with third-party data: zKillboard provides a market price history API
github.com
 and community aggregators (like EVEMarketer) could be used to reduce load. The backend will likely maintain a cache of commonly viewed items’ prices (updated periodically via background jobs) to provide quick responses to the frontend.
Industry Jobs and Assets: Through ESI’s industry endpoints, we can list a character’s active industry jobs (manufacturing, research)
wiki.eveuniversity.org
 and their mining ledger or blueprint copies. These authenticated calls will be made by the worker service at intervals (or on-demand when the user views an industry dashboard). Asset data (from /characters/{id}/assets/) can also be fetched and stored, possibly with a search index to let users quickly find items across their hangars. Because asset lists can be large, we will carefully design caching and updates (using ESI’s provided pagination and update endpoints).
Sovereignty & Universe Data: To support the map and strategic intel features, we will use public ESI data for sovereignty and universe. ESI’s “Sovereignty” endpoints provide the list of sovereignty-held systems and structures
wiki.eveuniversity.org
, which we’ll poll periodically (e.g. every few minutes) to update which alliance holds each system. Additionally, the “Universe” category in ESI covers static data like regions, constellations, systems, stargates, etc. We will bootstrap our database with the static universe data (either via ESI’s bulk endpoints or the Static Data Export) – including star system coordinates, region names, stargate connections, item types, etc. This is important for the map visualization and route planning.
Rate Limiting and Efficiency: All ESI calls will include a custom User-Agent and adhere to ESI’s rate limits and caching guidelines. ESI uses a token bucket rate limit on a sliding window
wiki.eveuniversity.org
. Our backend will throttle calls accordingly and leverage caching: many endpoints have built-in cache timers (e.g. character info might update every 30 minutes, market orders 5 minutes, etc.). The background jobs will be scheduled based on these timers to avoid redundant calls. We will also use ETags or last-modified where supported by ESI to fetch only differences. The job queue (Redis-backed) will ensure that spikes in requests (e.g. many users logging in at once) don’t overload ESI – jobs can be distributed over time.
Universe Map & Overlays Integration
An interactive map of New Eden with route planning and sovereignty overlays.
A standout feature is the EVE Universe Map with multiple data overlays. We will implement an interactive 2D map of all star systems, allowing zoom/pan and rich overlays for kills, routes, and structures. Key implementation details:
Star Map Rendering: We will leverage EVE’s static universe data to plot star systems on a map. Each solar system has x, y, z coordinates in the galactic coordinate system (available via ESI or SDE). We can normalize or project these into a 2D plane. For clarity and performance, we might use a flattened layout similar to Dotlan’s maps (organized by region and adjacency) rather than true scaled coordinates. The frontend will likely use a canvas or WebGL-based library (e.g. D3.js, PixiJS, or a React canvas component) to render thousands of systems and connections (stargate links) efficiently. Systems will be interactive (hover to see name, click for details). We will also provide a search to highlight specific systems.
Recent Kill Activity Overlay: The map will show recent PvP activity as a heatmap or markers. To achieve this, our backend will aggregate kills per system in near-real-time. We have two data sources: (a) ESI’s public “system kills” endpoint, which gives the number of ship/pod NPC kills in the last hour per system (useful for quick polling)
forums.eveonline.com
, and (b) live killmail feed from zKillboard for real-time data. We plan to use the universe system kills endpoint periodically for broad heatmap updates (since it’s lightweight and doesn’t require auth), and also process zKill’s feed to instantly flag a system when a new killmail comes in. The frontend can then highlight systems (e.g. glow or change color) based on kill count in the last X minutes. A gradient heatmap legend will indicate activity level. This gives users a quick intel view of where fights are happening.
Planned Travel Routes: Users can plan routes by selecting a start and destination (and optional waypoints). We will utilize ESI’s route calculation API (the “Routes” endpoint uses the game’s routing algorithm to return an ordered list of systems for a route)
wiki.eveuniversity.org
. When a user inputs a route request, the frontend calls our API, which queries ESI for the route (with parameters like shortest, safest route). The returned path (list of system IDs) is then highlighted on the map (connecting lines or a different color for those systems). We will allow waypoints or multi-destination trips by calling the route API sequentially for each leg (or potentially using a pathfinding algorithm on our side with the graph of stargates for complex routing). Additionally, we will incorporate jump bridges into route planning: If the user or their alliance has Ansiblex Jump Gates (player-built jump bridges), the user can input them or, if authorized, we fetch known jump gate links from ESI (via corporation structure endpoints for navigation structures). Our route-finding logic can then consider these as additional edges in the graph, offering routes that include jump bridge shortcuts. (Since ESI’s built-in route API won’t include player jump gates, we may implement a custom Dijkstra/A* algorithm for “fastest route with jump bridges” if needed, using our internal map data augmented with those connections.)
Jump Bridges & Stargates: The map will visually distinguish regular stargate links (connecting systems within a region or constellation) and player-made jump bridge links. Stargate connections come from static data (each stargate’s destination system is known via ESI’s universe/stargates endpoint). We will draw faint lines or curves between systems to represent these links. For jump bridges, if the user’s characters have access to that data (director roles to fetch structure info, or if we allow manual input of known coordinates), those will be drawn as dashed lines or a different color. This gives a strategic view of alternate travel networks. We’ll also overlay cyno beacons/jump routes if relevant (e.g. if planning a capital jump, showing range overlay might be a future enhancement).
Sovereignty & Ownership: We will overlay sovereignty data on the map to show which alliance holds each nullsec system. Using the ESI sovereignty map (public data of which alliance owns each system)
wiki.eveuniversity.org
, our backend will maintain an updated mapping of system→alliance. The frontend can color-code systems by alliance ownership (each alliance could have a distinctive color, perhaps generated or from a predefined palette). We can also draw region borders or highlight constellation boundaries if needed for visual grouping. A legend will map colors to alliance names, and the user can toggle this “Sov overlay” on or off. This overlay updates daily or on-demand (so if sovereignty changes after a big war, users can refresh to see the new borders). As an example, Project Eden (an EVE map tool) offers features like daily updated sov maps and jump planning
forums.eveonline.com
forums.eveonline.com
; our implementation will provide similar functionality integrated with our app’s data.
Additional Map Data: We will add other contextual overlays: for example, jump/jumpgate activity (ESI also has a “system_jumps” endpoint for number of jumps per system in last hour, which could indicate travel hotspots), Incursions (mark systems with active NPC incursions from ESI Incursions endpoint), or Faction Warfare status (show contested systems). These can be added as optional layers the user toggles. The map UI will include a control panel to toggle overlays (Kills, Sov, Incursions, etc.) and filter what is displayed.
The map integration will be implemented with performance in mind. We will use spatial indexing or quadtree partitioning to only render systems in view, and possibly precompute the positions for different zoom levels. The frontend will likely use a combination of SVG/canvas for static elements and HTML for tooltips/popups. We will ensure it is responsive and works on various screen sizes (using WebGL or Canvas for heavy rendering to maintain smoothness).
Frontend Design and Features
The frontend will be a modern single-page application (SPA) built with a popular framework (likely React with TypeScript, or Vue.js). The emphasis is on a responsive, visually appealing UI with intuitive controls, as the user experience is paramount. Key aspects of the frontend:
Layout and Styling: We will use a component library or design system for a professional look (e.g. Ant Design or Material-UI for React, or Vuetify for Vue). This provides ready-made responsive components (menus, tables, forms) and ensures consistency. A dark mode theme (akin to EVE’s in-game UI aesthetic) would suit the app’s context, with high-contrast highlights for important data (e.g. red for enemy kill alerts, green for positive events). The layout will likely include a sidebar or top navigation (for selecting major sections like Dashboard, Map, Market, Industry, etc.), a main content panel, and possibly real-time infoboxes or tickers.
Dashboard & Character Views: The app will have a dashboard summarizing key info for the user’s linked characters – e.g., skill training status, wallet balance, current location, active industry jobs, recent killmails, etc. This view provides an overview when a user logs in. Each character might have a dedicated page with detailed information (pulled from ESI) such as a skill list, ship fittings (from ESI fittings endpoint), assets inventory (with search/filter), and so forth. We will implement dynamic components like collapsible sections and tabs for organizing this data. For instance, a real-time activity feed might show events like “Character X’s killmail added” or “Industry job completed,” updating via WebSocket or polling.
Interactive Map UI: The Universe Map described above will be a primary interactive component. The UI will allow dragging the map, clicking systems for details, and showing context menus (e.g. “Set as start/destination”, “Show details” which might display system info such as security status, sovereign owner, recent kills in a sidebar). We’ll ensure smooth zooming and panning, possibly using a library like React-Leaflet (with a custom map projection) or a bespoke canvas solution for performance. The map should also be mobile-friendly: on smaller screens, it might switch to a different mode (perhaps list the waypoints or use a simplified region-by-region view).
Real-time Data and Notifications: Using WebSockets (or long-polling as fallback), the frontend will receive push updates for certain events. For example, when a new killmail is received via our backend, if it’s relevant to the user (say, occurs in a system they are watching or involves their alliance), we can display a notification or highlight on the map immediately. Similarly, if the user’s character goes offline/online or a new market order is fulfilled, these could reflect live. A “notifications” component might display recent events, and possibly integrate with browser notifications (with user permission) for important alerts (e.g., structure under attack for their corp).
Market and Industry UI: We will build specialized frontend components for market browsing and industry management. The market interface could allow the user to search for an item and see current buy/sell prices in various regions (using our backend which pulls ESI market orders). We might include price charts (using a charting library like Chart.js or D3) for item price history over time – leveraging either ESI’s historical data or zKill’s price history API
github.com
. For industry, an interface to show all ongoing jobs across characters, profitability calculators, and possibly blueprint library (requiring some SDE data) will be included. These pages will be rich with tables and charts, so we’ll ensure they are paginated and efficient (using server-side paging for large datasets).
Responsive and Mobile-Friendly: From the outset, we will design the UI to be responsive. Using CSS flexbox/grid and the component library’s responsiveness features, the layout will adapt to different screen sizes. On mobile, some complex views (like the star map) may default to simplified displays or require horizontal scrolling. We’ll test on common resolutions to ensure usability remains high. The goal is that a user could comfortably check their data or view the map from a phone or tablet, not just desktop.
Usability & Aesthetics: We will follow UI/UX best practices: clear typography, appropriate use of color (e.g. security status colors for systems, or red/green for loss/profit), and provide help tooltips or an onboarding guide for new users. The design will align with EVE’s sci-fi theme – for example, we might use EVE’s iconography (there are image servers for EVE item icons, alliance logos, etc., which we can embed via URL) to enrich the interface. Real-time elements will have loading spinners or skeleton screens to handle data latency gracefully.
Given the complex data, we will also implement client-side caching/state management (using Redux or Vuex/Pinia) to avoid redundant API calls – e.g., if the user has fetched an alliance’s info once (for sov display), reuse it across components. The frontend will communicate with the backend via JSON REST calls (and perhaps some WebSocket endpoints for pushes), and all API usage will be abstracted in a client service layer for cleanliness. We will document the frontend code to make it easy for developers to extend (for instance, adding a new panel for “Fleet Manager” in future would follow the established patterns).
Backend Services and Data Flow
The backend is composed of multiple services (as outlined in Architecture Overview), each responsible for a subset of tasks. They work in concert to provide a seamless experience: the API server handles incoming requests synchronously, while background workers handle heavy lifting asynchronously. Here we detail the backend components and their interactions:
REST API Layer: The API service (possibly built with FastAPI or Flask if Python, or Express/NestJS if Node) will present organized endpoints to the frontend. This includes endpoints like /characters/{id}/... for character-related data, /map/routes for route calculation requests, /market/{itemId} for market prices, etc. This service acts as a BFF (Backend-For-Frontend), aggregating data from the database and other services as needed. For example, when the frontend needs to load the dashboard, an API call to /user/overview might gather the user’s characters, query the database for cached stats (wallet, skill points), and return a JSON payload. If some data is stale or missing (e.g. character’s latest wallet balance), the API can trigger a background job to refresh it from ESI, but still quickly return cached data to the user (ensuring fast UI). The API will enforce security – checking the user’s session or token to ensure they can only access their data. We will likely use JWT tokens for the session (issued at user login and stored in HTTP cookies or localStorage) to authenticate API requests. Each request will be validated so one user cannot fetch another user’s info (the API will map incoming JWTs to user accounts and filter data accordingly).
Worker and Task Queue: The background job processor (e.g. Celery if using Python) is the engine for handling tasks that don’t need to be done in real-time or are too slow for a sync request. This includes: refreshing ESI data, processing large data sets, and periodic polling. We’ll define tasks such as refresh_character(char_id), update_market_orders(region_id), fetch_killmails(char_id), update_sovereignty(), etc. When a user links a new character, for instance, the API will enqueue a job to fetch all that character’s info (assets, contacts, etc.). The task queue (with Redis broker) decouples these operations from the web request – the user sees an immediate response (“Character linked, data is syncing...”), and the heavy data pull happens in the background. We will run multiple worker processes so that many jobs (like updating kill counts and market data) can run concurrently.
Scheduling: Many ESI endpoints should be polled periodically to keep our local cache up to date. For example, sovereignty data could be fetched every 15 minutes, killmail stats every few minutes, corporation member lists maybe hourly. We will use a scheduler (Celery Beat if Python, or a cron inside a dedicated container, or even Kubernetes CronJobs) to dispatch these tasks on a schedule. The schedules will align with ESI’s cache intervals – e.g., if the /sovereignty/map endpoint updates every 3600 seconds, we schedule it accordingly. The scheduler will also handle token refresh tasks: although our implementation can refresh on-demand, it’s good to proactively refresh tokens nearing expiration in a background job to avoid any user-facing delays.
Database Design: A PostgreSQL database will store persistent data. The schema will include tables for Users, Characters, Corporations, Alliances, and various EVE data needed for the app. For example:
Users: (id, email, password_hash or OAuth identity, etc.) – representing application users.
Characters: (id, user_id, char_name, corporation_id, etc. plus OAuth tokens) – each linked EVE character. We also store metadata like last known location, total SP, ISK balance, etc., updated regularly.
Corporations/Alliances: Basic info (name, ticker, ID, alliance membership) to support displaying names from IDs. These can be filled in as they appear (on-demand via ESI’s universe name resolution if needed) or pre-seeded for known entities.
Killmails: We may store killmail records (kill ID, timestamp, system, involved party IDs, etc.) for kills involving the user’s characters or for recent global kills. Storing all killmails in New Eden would be huge, so we’ll likely not keep everything – instead, maybe cache the last X days of global kills or just statistics per system. We will definitely store personal killmails for a user’s characters so they can review their kills/losses.
Market Data: Possibly a table for item prices (item_id, region_id, last_update, buy_avg, sell_avg, etc.) to cache market queries. We might integrate an in-memory cache or use Redis for ephemeral caching, but some data (like price history for graphs) we can store in the DB if we aggregate it.
Sovereignty: A table mapping system_id -> owner alliance_id (updated regularly) to quickly answer “who owns this system” in the map overlay.
Universe Static Data: Tables for Regions, Constellations, Systems, Stargates, etc., populated from the static dump or ESI’s universe endpoints. These will help with map drawing and route planning. (Each system entry can include coordinates, security status, region id, etc.)
The database will be initialized with key static data (we can use the EVE SDE in YAML/CSV format to populate regions, systems, item types). By having this locally, we avoid calling ESI for static info repeatedly. We will also implement migrations to update static data if needed (CCP rarely adds new systems, but if they do, we update our DB).
Caching Layer: We will use Redis both as a message broker for Celery and as a general cache. For instance, after fetching an alliance’s information from ESI (name, ticker, logo), we can cache that in Redis so that subsequent requests needing the alliance name don’t always hit the DB or ESI. Similarly, heavy aggregation results (like a precomputed list of “top 10 killers in last 24h in this region”) can be cached. We’ll define sensible TTLs for cache entries based on how fresh data needs to be (market prices maybe 10 minutes, kill counts maybe 1 minute, etc.). The cache also helps share state between the API server and workers – e.g., a worker can publish an event to a Redis pub/sub channel which the API (or a WebSocket gateway) listens to in order to push updates to clients (this could be used for instant kill notifications without a separate push service).
Security & Data Access: The backend will enforce strict access control. Each API call is authenticated via the user’s token; the service then queries only data for that user’s characters. For multi-user support, every character record links back to a user, and any corp-wide data (like corp wallet or structures) is only visible if the user’s character has the required corp roles and has authorized the scope. We will not store EVE account passwords or such – all authentication is via tokens from CCP. Sensitive data (refresh tokens, user passwords if any) will be encrypted at rest. Additionally, we will implement input validation and output filtering on all endpoints to prevent injection attacks or leakage of data.
Logging and Monitoring: We will include robust logging in each service – e.g., logging ESI call results, errors, and performance metrics. This helps in debugging and also in not hitting ESI limits (we can quickly see if a certain endpoint is being called too often). In production, we might deploy an ELK stack or use a cloud logging service to aggregate logs. For monitoring, we can include health checks for each container (Docker healthcheck or Kubernetes liveness probes) and possibly integrate Prometheus/Grafana for metrics (like number of kills processed per minute, or API response times). These DevOps considerations will ensure the backend remains healthy and scalable as usage grows.
In summary, the backend architecture is service-oriented: the API handles client interaction, workers handle data sync, and the database/redis handle state, all orchestrated via Docker. This aligns with real-world projects like SeAT, which uses a front-end web service plus worker and scheduler containers to interface with ESI
eveseat.github.io
. Our system will similarly ensure that heavy lifting (ESI polls, data crunching) happens asynchronously, keeping the user experience snappy.
Security and Access Control
Security is critical given we are dealing with authenticated EVE accounts and potentially sensitive data. Our plan includes multiple layers of security:
OAuth2 Secure Flow: We rely on CCP’s secure OAuth2 for authentication. Users will be redirected to the official EVE Online SSO login page to enter credentials – our app never sees their password. After granting scopes, we receive an authorization code which we exchange for tokens via a server-to-server call (using our secure client secret). This exchange happens on the backend to avoid exposing the secret. Tokens (access and refresh) are then stored in our database. We will encrypt these tokens at rest (using a symmetric key or the database’s encryption functions) so that even if the DB is compromised, the tokens are not plaintext. The token storage table will include metadata like token expiration and scopes.
Multi-Character Handling: When a user links multiple characters, each gets its own token set. In our UI and API, we will isolate data per character unless the user explicitly wants a merged view. For example, a user can switch the “active character” context in the UI to view specific details or perform actions (similar to how EVE Portal app works). This ensures that when the app calls an ESI endpoint, it uses the correct character’s token (we will track which token corresponds to which character ID and only use that for that character’s data calls). For actions that involve multiple characters (say, a combined asset view), the backend will internally call ESI for each character’s data and then merge results for display, but still respecting that the user owns all those characters.
Scope Management: We will request only the necessary scopes to minimize risk. The scopes requested will cover the features we need, and we will document these to the user when they authenticate (so they know what access they are granting). If in future we add features requiring new scopes (e.g. sending mails, managing fittings via ESI), the app would prompt the user to re-auth with the additional scopes. We’ll also implement graceful degradation: if a user chooses not to grant certain scopes, the features depending on them will be disabled for that user. For instance, if they don’t grant esi-industry.read_character_jobs.v1, we simply won’t fetch industry jobs for them.
User Accounts and Roles: The application will have its own user account system (likely with email/password or OAuth login via an existing service). This account is what the user actually logs into on our app, and then links their EVE characters. Passwords (if used) will be stored hashed (using strong algorithms like bcrypt). Alternatively, we might allow logging in with just an EVE character as identity (SSO) – in that case, the first character they login with creates an account. In either scenario, we will have an option for two-factor authentication (TOTP or email verification) for added security on the app account. If the app is multi-tenant or corp-focused, we might incorporate user roles/permissions (e.g. an admin user can see corporation-wide dashboards if corp mates link their characters, etc.). By default, however, each user can only access data for characters they have authenticated.
Data Partitioning: In the backend, all queries will filter by user or character ID to prevent leakage. We will double-check all joins or lookups to avoid any scenario where one user’s data could appear in another’s result. For example, if we store all killmails in one table, queries for a user’s killboard will always include WHERE character_id IN (their chars). We will also design the API endpoints URLs to include the character or user context, and the backend will verify that the authenticated user owns that character ID.
Secure Communication: All network communication will be over HTTPS (both between browser and server, and server to ESI or other external APIs). In deployment, Traefik or Nginx will handle TLS termination and enforce modern TLS standards. We’ll obtain certificates (likely via Let’s Encrypt in production). We will also enable HSTS and secure cookies for session tokens to mitigate man-in-the-middle risks.
Protection of Sensitive Keys: The EVE SSO client secret, JWT signing keys, database credentials, etc., will not be hard-coded. In Docker/Kubernetes, we will provide these via environment variables or secret management tools (e.g. Docker secrets or Kubernetes Secrets). The code will read from env variables like EVE_CLIENT_ID, EVE_CLIENT_SECRET. This way, secrets are not exposed in code repositories. We will also restrict access to these values at runtime (for example, in Kubernetes only the pods needing the secret have access).
Refresh Token Safety: Refresh tokens are long-lived and need careful handling. Our app will never send refresh tokens to the client side. They are only used server-side to get new access tokens. We will implement a refresh mechanism in the backend – for instance, a scheduled job that checks for tokens expiring in the next N minutes and refreshes them proactively, or a just-in-time refresh if an API call fails with “token expired”. We’ll also design for the scenario where a refresh token becomes invalid (if the user revokes permissions via the EVE website or it expires). In that case, we’ll detect the refresh failure and prompt the user to re-authenticate.
Audit and Logging: All login attempts, token refreshes, and key user actions will be logged. We can maintain an audit trail of when a character was linked or unlinked, and when data was last pulled. If suspicious activity occurs (e.g. a user account suddenly links many characters or makes excessive requests), we can flag it. We might also integrate basic rate-limiting on our API (to prevent a single user from spamming requests and possibly causing our app to hit ESI limits).
Third-Party Integration Security: We will consume data from zKillboard and possibly others. We’ll do so in read-only ways (HTTP GETs, WebSocket listen). We must ensure that any data from these sources is sanitized before use (though it’s mostly numeric/string data, we should still treat it cautiously if ever displayed). If we embed killmail info, we’ll guard against HTML in killmail victim or attacker names (unlikely but we’ll escape strings in the frontend to be safe).
Overall, the security model ensures least privilege (only necessary scopes, only user’s own data) and defense in depth (encrypted storage, secure transport, thorough authentication). By following CCP’s third-party developer guidelines and general web security best practices, we will protect both our users and the game’s data integrity (noting that CCP explicitly forbids any malicious use of their APIs
wiki.eveuniversity.org
 – our app will comply fully, using data only to enhance user experience, not to cheat or abuse in-game systems).
DevOps and Deployment Strategy
We aim for a smooth development workflow and robust deployment pipeline, using containerization to ensure reproducibility from local dev to production. Below are the DevOps plans and deployment considerations:
Dockerization: Every component of the app will have a Docker image. We will maintain a base Dockerfile for the backend (installing necessary dependencies, then adding our code), one for the frontend (perhaps using a multi-stage build: first stage builds the React app, second stage uses an Nginx image to serve the static files), and we will use official images for services like Postgres, Redis, Traefik. In development, Docker Compose will orchestrate these: a docker-compose.yml that defines all services, networks, and volumes. For example, we’ll have a service for web (our API, exposing port 8000 internally), worker (running the same image but with a command to start Celery workers), scheduler (running Celery beat), frontend (Nginx serving UI on port 3000 internally), db (Postgres with a mounted volume for data), redis, and proxy (Traefik mapping routes). We will mount code volumes in dev to allow hot-reload for the API and live reload for the frontend. In production, we’ll use images built from a CI pipeline (no code mounting, just run the containers).
Continuous Integration (CI): We will set up a CI pipeline (e.g. using GitHub Actions or GitLab CI) to automate building and testing. On each commit or pull request, CI will:
Run unit tests for backend and frontend (ensuring new changes don’t break existing functionality).
Lint and static-check the code (for quality and security issues).
Build the Docker images for the app (tagged with commit hash or version number).
Possibly run integration tests by spinning up the Docker Compose and running test scenarios (this ensures the whole stack works together).
Only if tests pass will the pipeline proceed to deployment (for main branch merges). This gives developers rapid feedback and maintains code reliability.
Continuous Deployment (CD): For deployment, we have a couple of options:
If using a container platform like Kubernetes, we will create manifests or use Helm charts to define our deployment. Each service (api, worker, frontend, db, etc.) can be a Deployment in K8s, with a Service for networking. We’ll likely use a Managed DB (e.g. AWS RDS for Postgres) in production instead of a container for the database, to have reliable storage and backups. For Kubernetes clusters (could be EKS on AWS, GKE on GCP, or a cluster on Hetzner), we’ll configure autoscaling for the API and worker deployments so they can scale out under load (for example, if many map requests come in, scale API pods; if many background jobs queue up, scale worker pods). We’ll also use Kubernetes Secrets to store things like the OAuth client secret, which the pods can consume as env vars.
If opting for a simpler route, we could use Docker Compose in production on a single VM or a small cluster. For instance, a Docker Compose on a Hetzner cloud VM or an AWS EC2 instance could run the stack. In that case, we’d ensure the VM is secured, Docker is up to date, and we use something like Watchtower or a CI hook to pull new images and restart containers on updates. However, for reliability and scalability, Kubernetes is preferred as we grow.
We will also integrate CI/CD pipeline to automate deployment: after CI builds the images and runs tests, it can push the images to a registry (Docker Hub or an AWS ECR/GCP Artifact Registry). Then, using either infrastructure scripts or GitOps, the new images can be deployed. For example, we might use Argo CD or Flux (GitOps tools) to watch a repo for image tag updates and apply them to our K8s cluster. Alternatively, a simpler approach: use an action to SSH into the server and run docker-compose pull && docker-compose up -d for a Compose-based deployment. The exact choice will depend on the team’s familiarity and the hosting environment.
Hosting Considerations: We have flexibility in hosting:
AWS: We could use ECS (Elastic Container Service) or EKS (Kubernetes) to host containers, with an Application Load Balancer in front. AWS has Cognito for identity (though we mainly rely on EVE SSO), and services like S3 could store logs or static files. AWS’s RDS can host Postgres, and ElastiCache for Redis in production for high performance. This is a robust but potentially costly setup.
Google Cloud (GCP): GKE (Google Kubernetes Engine) would similarly handle the K8s deployment. Or we could even use Cloud Run for the API and workers (since they are stateless containers) – Cloud Run auto-scales and is fully managed, which might simplify deployment (each component could be a separate Cloud Run service, communicating via a VPC or pub/sub). GCP’s Cloud SQL can provide the Postgres backend.
Hetzner or other VPS: A cost-effective approach is to rent a VM or two on Hetzner, DigitalOcean, or similar, and run Docker Compose or a small Kubernetes (k3s) cluster there. Hetzner even has a managed Kubernetes offering now, which could combine lower cost with modern deployment. We’d handle our own CI runner or use GitHub Actions to deploy to it. We need to ensure we have proper backup of the database volume (could use automated snapshots or tools like pg_dump to cloud storage).
Environment Configuration: We’ll maintain environment-specific config via env files or Kubernetes config maps. For example, we’ll have a .env.development and a .env.production. These will include settings like DEBUG mode, allowed origins for CORS, and API base URLs. The OAuth callback URL will differ in dev (localhost) vs prod (our domain). We must configure those in the EVE dev portal as well. Docker Compose will use the env file for local development. In production K8s, we’ll set these as needed (like EVE callback URL = our hosted domain).
Domain and HTTPS: We will set up a domain name for the application (e.g. myeveapp.com). In the reverse proxy (Traefik/Nginx), we will configure routes: the main web app (frontend) likely served at / and API at /api or a subdomain (api.myeveapp.com). Traefik can automatically get Let’s Encrypt certificates for the domain. If using Nginx, we could manually provision certs or also use Let’s Encrypt via certbot. We’ll enforce HTTPS redirection.
Scaling & Load Testing: We will conduct load tests to ensure the app can handle expected traffic. For example, test the map with thousands of systems to ensure rendering is efficient, test the API under concurrent usage (which might require tuning Gunicorn workers or Node cluster settings). With containers, scaling is as easy as increasing replica counts. For stateful parts: Postgres can be vertically scaled or we can add read replicas if needed (though most writes are user-specific so one primary is fine). Redis can be clustered or given more memory if needed (mostly for caching and queue transient data). We’ll also consider using a CDN for static assets (the React bundle, images, etc.) – e.g. CloudFront or Cloudflare – to offload that from our servers and improve global load times.
CI/CD for Infrastructure: If using Kubernetes, we might codify the infrastructure in IaC (Infrastructure-as-Code) tools like Terraform (to provision cloud resources) and Helm for app deployment. This ensures that we can reproduce the environment and track changes in source control. For a smaller setup, a simple Ansible script or Docker Compose config might be enough to stand up a new environment. In any case, we will document the deployment steps clearly for the team.
Backups and Recovery: We will implement regular backups for the database (this is crucial as it contains user data and token credentials). If using managed DB, enable automated backups; if self-hosted, use a cron job to dump the DB daily to an offsite location. Likewise, if any user-uploaded data or cache needs backup (though mostly we won’t have user-generated content aside from settings), ensure those are captured. We will test restoration procedures as well.
Monitoring & Alerts: In production, we’ll employ monitoring. If on Kubernetes, use Prometheus + Grafana for metrics, or use a cloud’s monitoring suite (CloudWatch on AWS, etc.). We’ll monitor key metrics: CPU/memory of containers, response latency, error rates, ESI error responses, etc. Alerts will be set up for critical issues (e.g. if the API is down or if ESI calls start failing continuously indicating maybe an auth issue). We can integrate with Opsgenie or simply email the dev team on such events.
CI/CD Pipeline Example: To illustrate, using GitHub Actions, we might have workflows like:
build.yml: on pull request, build and test.
deploy.yml: on push to main (or on manual trigger for release), build images, push to registry, then use ssh or Kubernetes action to deploy. For Kubernetes, we might have a step to run kubectl set image deployment/api myapp-api:tag etc., or use Helm upgrade. This will roll out the new version with zero (or minimal) downtime.
By implementing these DevOps practices, the project remains maintainable and resilient. Developers can spin up the entire stack locally with one command (docker-compose up) and get the same environment that runs in production. Deployment to production is automated and consistent, reducing the chance of human error. Our use of Docker and potentially Kubernetes not only satisfies the requirement of a Dockerized architecture but also sets the stage for scaling the app to many users and continuous improvement.
Insights from Existing Projects
Before implementation, it’s wise to learn from similar open-source EVE Online projects to not reinvent the wheel and to adopt proven solutions:
SeAT (EVE Seat): SeAT is a popular open-source EVE corporation management tool. Its architecture offers valuable lessons. It uses a modern web stack (Laravel/PHP for backend, with a web UI) and is fully containerized. In SeAT 5.x, the team uses Docker Compose with multiple containers: a front-end web service, background workers, a scheduler for ESI polls, Redis for queues, and MariaDB for storage
eveseat.github.io
. This validates our microservices approach. SeAT’s documentation emphasizes the need to register the app with CCP and configure ESI scopes properly
eveseat.github.io
 – confirming our plan to do so. We can also look at SeAT’s implementations for handling ESI tokens, refresh logic, and data models. For example, SeAT likely already defines database schemas for characters, corporations, etc., which could inspire our own (ensuring we capture all relevant fields like character titles, corp roles, etc.). Additionally, SeAT provides a plugin system for additional features; while our app is a different scope (focusing more on map and multi-character dashboards), we might reuse some concepts or even libraries from SeAT (perhaps their ESI client code or their approach to background job scheduling).
Pathfinder & Intel Map Tools: Pathfinder is an open-source wormhole mapping tool, and other tools like EVELiveIntel and Project Eden focus on map visualization
pathfinder.eve-linknet.com
forums.eveonline.com
. From these, we glean techniques for map drawing and intel integration. For instance, EVELiveIntel (on GitHub) centralizes intel reports on a map; it might provide code or algorithms for efficiently rendering the universe map and handling real-time position updates
github.com
. Project Eden (which we cited earlier) demonstrates that it’s feasible to have an in-browser map for New Eden with jump planning and sov—our map feature is essentially building upon that concept
forums.eveonline.com
. By examining these projects (if source is available), we can shortcut some development: possibly obtaining a JSON of all system coordinates, or a list of adjacency that we can use for route planning. Also, seeing how they handle performance (maybe clustering many systems, or only drawing certain labels at certain zoom levels) will inform our implementation.
zKillboard Integration: zKillboard is the de-facto kill tracker for EVE, and it offers APIs that we intend to use. We have confirmed via zKill’s documentation that they provide a RedisQ service and REST endpoints for killmails
github.com
. We can utilize zKill’s experience in handling kill data: for instance, zKillboard encourages third-party apps to use their websocket instead of polling ESI for every kill, which we will do. Also, zKillboard’s data model (how they structure killmails, the meaning of fields like victim, attackers, zkb meta info) can guide how we store or process kill data. If zKillboard is open source (it has a GitHub repo), we might even look at its source to see how it caches killmails or handles the volume (zKill uses a combination of datastore and in-memory caching). Additionally, we will integrate with zKill’s statistics API to fetch things like top killers, ship meta stats, etc., which can enhance our app’s “intel” aspect. We will follow any usage guidelines they have (like rate limits or requiring a user agent string). Since our app will provide some similar killboard functionality (at least for the user’s own kills or corp kills), referencing zKill’s UI/UX for kill presentations (such as how they display killmail details, or the concept of efficiency, ISK destroyed) will help shape our features.
Community and CCP Resources: We will also lean on community resources. The EVE Dev community is active: the ESI issue tracker on GitHub
wiki.eveuniversity.org
, the EVE Online forums (Third-Party Developers section), and the EVE University Wiki (for up-to-date ESI quirks) are all valuable. For example, recent dev blogs (“ESI Delivered: The Next Chapter”
wiki.eveuniversity.org
) might discuss upcoming changes to the API that we should design for. We should ensure our plan is up-to-date with any new ESI developments (as of 2025, ESI is stable but has had some removals like bookmarks, which won’t affect us
wiki.eveuniversity.org
).
By studying these projects and documents, we mitigate risk and gain reusable components. We may even integrate directly with some – for instance, if SeAT has an API, we might use SeAT as a backend for corp management features instead of duplicating them. However, since our app is tailored for individual users (and possibly small group use) with an emphasis on the map and multi-character integration, we’ll implement most features in-house, using the others as reference implementations.
Conclusion and Next Steps
With this development plan, we have outlined a comprehensive application that leverages the full range of EVE Online’s APIs and presents the data in a powerful, user-friendly way. The architecture is designed for scalability and maintainability, using Docker containers to separate concerns and allow flexible deployment. We have detailed the integration of ESI (EVE Swagger Interface) for all major data domains
wiki.eveuniversity.org
, ensuring that character, corporation, killmail, market, and sovereignty data (among others) are available to our app’s users with minimal friction. The inclusion of an interactive universe map with advanced overlays (kills, routes, jump bridges, sov, etc.) will provide a visually rich experience, turning raw data into actionable intelligence on New Eden’s landscape. Our choices of a modern frontend framework and a robust backend with REST API + background workers strike a balance between real-time interactivity and reliable batch processing. Security and privacy have been woven into the plan, from OAuth2 token handling
wiki.eveuniversity.org
 to multi-user data segregation and secure deployment practices. Finally, our DevOps strategy ensures that as we develop, we can continuously integrate and deploy changes, scaling the infrastructure on platforms like AWS, GCP, or Hetzner as needed. By summarizing lessons from comparable projects like SeAT and zKillboard, we stand on the shoulders of proven solutions rather than starting from scratch
eveseat.github.io
github.com
. This document serves as a blueprint for developers to begin implementation. Next steps will include setting up the repository structure (perhaps splitting into frontend and backend directories), writing initial Dockerfiles, and scaffolding the OAuth2 flow with CCP’s SSO – as that is a prerequisite to any authenticated ESI calls. From there, we can incrementally build out each feature: e.g., start with character login and basic data retrieval, then add the map visualization, then layer in killmail streaming, and so on, verifying each component with unit and integration tests. By following this plan, the development team can create a feature-rich, Docker-based EVE Online companion application that is both powerful for veterans and accessible to newcomers, all while being maintainable and scalable for future growth.
Citations

Docker Installation (5.x) - SeAT Documentation

https://eveseat.github.io/docs/installation/docker_installation/

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

Docker Installation (5.x) - SeAT Documentation

https://eveseat.github.io/docs/installation/docker_installation/

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

Home · zKillboard/zKillboard Wiki · GitHub

https://github.com/zKillboard/zKillboard/wiki

Home · zKillboard/zKillboard Wiki · GitHub

https://github.com/zKillboard/zKillboard/wiki

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

Home · zKillboard/zKillboard Wiki · GitHub

https://github.com/zKillboard/zKillboard/wiki

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

Looking for a small app idea - Third Party Developers - EVE Online Forums

https://forums.eveonline.com/t/looking-for-a-small-app-idea/317360

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

Project Eden - An EVE Online - In-game Map Emulator and Jump planner - Third Party Developers - EVE Online Forums

https://forums.eveonline.com/t/project-eden-an-eve-online-in-game-map-emulator-and-jump-planner/497320

Project Eden - An EVE Online - In-game Map Emulator and Jump planner - Third Party Developers - EVE Online Forums

https://forums.eveonline.com/t/project-eden-an-eve-online-in-game-map-emulator-and-jump-planner/497320

Home · zKillboard/zKillboard Wiki · GitHub

https://github.com/zKillboard/zKillboard/wiki

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

Pathfinder Community Edition

https://pathfinder.eve-linknet.com/

jeremieroy/EVELiveIntel: Live Intel Map for EVE Online - GitHub

https://github.com/jeremieroy/EVELiveIntel

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

EVE Stable Infrastructure - EVE University Wiki

https://wiki.eveuniversity.org/EVE_Stable_Infrastructure