# Literature and Project Survey for Cellular Network-Aware Routing, Geo-Deferred Notifications, and Wrong-Way Driver Detection Beyond Ramps
## Overview
This report surveys academic research and notable past projects relevant to three hackathon proposal themes: (1) cellular network-aware routing, (2) geo-deferred notifications, and (3) wrong-way driver detection beyond ramps.
For each theme it outlines key problem formulations, representative algorithms or systems, available datasets or platforms (e.g., OpenStreetMap, crowdsourced coverage data), and ideas that can be adapted to a student-scale prototype.
## 1. Cellular Network‑Aware Routing
### 1.1 Problem framing in the literature
Traditional route planners minimize time or distance without explicitly accounting for cellular connectivity, which is increasingly critical for navigation, ride-hailing, and connected-vehicle applications.[^1][^2]
Research therefore defines *connectivity-aware shortest paths* that trade off physical path length with signal quality metrics such as minimum or average received signal strength along a route.[^2][^1]
Crowdsourced measurements from smartphone apps and public coverage maps are commonly used as inputs because operators rarely publish fine-grained per-road signal data.[^3][^4][^5]
### 1.2 Connectivity‑Aware Route Planner (CARP)
A well‑known project is the Connectivity‑Aware Route Planner (CARP), introduced at IEEE PerCom Workshops 2016.[^1][^2]
CARP integrates OpenStreetMap (OSM) road graphs with crowdsourced signal-strength measurements from OpenSignal to compute routes that optimize different connectivity objectives (classical shortest path, threshold-based routing ensuring signal above a minimum, and bounded-threshold routing that trades distance for better worst‑case signal).[^2][^1]
Evaluation on a medium-sized city shows that accepting a roughly 15 percent longer physical route can improve worst‑case signal strength by around 8–9 dBm, demonstrating a clear trade‑off front that your prototype could visualize.[^1][^2]
### 1.3 Crowdsourced cellular coverage analytics
Several commercial and research efforts collect large‑scale crowdsourced mobile network KPIs via SDKs embedded in apps or dedicated measurement tools.[^3][^4]
Examples include RantCell and Weplan Analytics, which capture signal power (RSRP/RSRQ), network type, and connectivity loss events to create coverage heatmaps and identify problem zones such as frequent drops to 2G or complete outages.[^4][^3]
Recent work on mobile coverage analysis using crowdsourced data further formalizes coverage assessment at cell and site level, providing methodologies for aggregating noisy measurements to robust per‑segment coverage scores.[^5]
### 1.4 Operator‑provided coverage maps
GSMA Intelligence maintains global raster datasets and interactive coverage maps sourced directly from mobile network operators, giving a coarse but authoritative view of where 2G/3G/4G/5G services are available.[^6][^7]
These maps are updated regularly and can be used to seed connectivity estimates where crowdsourced data is sparse, or to validate that your inferred poor‑coverage segments align with known weak areas.[^7][^6]
### 1.5 Cellular positioning and its implications
Work on 5G positioning demonstrates that synchronization signals in commercial networks can localize static users with roughly 8–10 m accuracy in non‑obstructed environments after compensating for base‑station clock offsets.[^8]
Although your prototype does not need such sophistication, these results support the assumption that cell‑level coverage and signal metrics can be meaningfully aligned to specific road segments for routing decisions.[^8]
### 1.6 Past systems and tools you can borrow from
- Map matching and traffic‑aware routing projects (e.g., GraphHopper’s map matching) show how to associate GPS traces with OSM edges and maintain edge IDs for routing, which is exactly what you need to attach coverage statistics to individual road segments.[^9][^10]
- Crowdsourced quality-of-experience analytics platforms demonstrate visualizations like signal-strength heatmaps, drop‑zone clustering, and KPIs such as percentage time with 4G/5G or disconnection minutes per day that could inspire your UI.[^3][^4]
- Zero‑shot cellular trajectory map‑matching work aims to align coarse cellular trajectories to road networks, suggesting methods for dealing with noisy location data when measuring coverage along candidate routes.[^11]
### 1.7 Prototype design implications
Academic work indicates that a useful connectivity‑aware routing prototype should:

- Use a standard road graph (OSM) and perform basic map‑matching of sample traces or simulated trips.
- Attach per‑edge metrics like average signal level, fraction of time with no coverage, or probability of drop‑out based on crowdsourced or synthetic measurement logs, following methodologies from CARP and later coverage‑analysis papers.[^1][^2][^5]
- Implement at least two routing policies (fastest vs most‑connected) and let users control the weight between travel time and connectivity, reproducing the distance–signal trade‑off reported in CARP.[^2][^1]
- Provide visual overlays (heatmaps, edge coloring) and a scalar “Connectivity Score” for each route to make differences interpretable, borrowing visualization ideas from crowdsourced analytics dashboards.[^3][^4]
## 2. Geo‑Deferred Notifications
### 2.1 Background: interruptibility and context‑aware notifications
Human–computer interaction research has extensively studied when to deliver mobile notifications to minimize disruption and maximize responsiveness, often under the label of *interruptibility* or *opportune moments*.[^12][^13]
Early systems such as SenSay, SCAN, and InterruptMe used sensors and contextual cues (activity, conversation, application usage) to suppress or defer notifications until breakpoints, reducing cognitive load and improving task focus.[^13][^14][^12]
A broader body of work, including attention‑aware middleware like Attelia and frameworks like Oasis, confirms that timing and contextual relevance matter more than sheer urgency for perceived intrusiveness.[^14][^15]
### 2.2 User‑defined and rule‑based deferral
The “Snooze!” study introduced an Android app that lets users defer notifications either for a user‑defined time interval or until a specified moment, and analyzed how people choose to delay or immediately address different notification types.[^13][^16]
Findings suggest that users are willing to delay many non‑urgent alerts but want fine‑grained control over what gets deferred and for how long, motivating rule‑based or machine‑learned policies that respect personal preferences.[^16][^13]
Other work, such as PrefMiner and intelligent notification frameworks, mines user histories to infer rules (e.g., “mute social media during work hours unless tagged directly”), which could be combined with geo‑based conditions in your project.[^17][^16]
### 2.3 Context‑aware notification services
A context‑aware notification service proposed by researchers at Cambridge explored issuing notifications based on likelihood estimates of situations of interest (e.g., a person being at the office with high probability), highlighting how raw location and context streams can be turned into probabilistic triggers rather than simple on/off geofences.[^18]
More recent frameworks for intelligent mobile notifications model physical, cognitive, and emotional context to predict attentiveness and receptivity, then schedule delivery for predicted opportune moments.[^17]
These systems typically use multimodal sensing (location, motion, app usage) and machine learning, but the core design idea—queueing notifications and releasing them when context conditions are met—is directly applicable to geo‑deferred delivery.[^17]
### 2.4 Geo‑fencing and location‑based push in industry
Commercial push providers and geofencing platforms describe architectures where notifications are triggered when devices enter or dwell within virtual geographic zones.[^19][^20]
Best‑practice documents emphasize challenges highly relevant to your proposal, including over‑triggering in dense geofence setups, GPS drift causing false positives, and failures due to OEM background restrictions or poor connectivity that lead to missed or delayed pushes.[^20][^19]
Vendors respond with techniques like blending GPS with Wi‑Fi/Bluetooth, enforcing dwell‑time thresholds, and implementing recovery mechanisms that fetch missed notifications once connectivity resumes—all patterns a hackathon prototype could emulate in simplified form.[^19]
### 2.5 Geo‑context‑aware data distribution
Research on geo‑context‑aware IoT data distribution shows how including geo‑filters can reduce message volume by orders of magnitude when only a subset of clients in relevant locations actually need updates.[^21]
In evaluation scenarios, distributing data to only about 1 percent of potential recipients based on geo‑context reduced hourly message counts from hundreds of millions to a few million, demonstrating the bandwidth and scalability benefits of geographic deferral and filtering.[^21]
### 2.6 Prototype design implications
The literature suggests several concrete decisions for a geo‑deferred notification prototype:

- Maintain a queue of pending notifications annotated with metadata (urgency, topic) and simple rules specifying where/when they can be delivered, inspired by user‑defined snoozing and rule‑based deferral systems.[^13][^17][^16]
- Use geofenced “good coverage” or “user‑preferred” zones along a trip as release conditions, leveraging coverage estimates from the routing work or known high‑signal segments.[^1][^2]
- Implement simple priority handling so urgent alerts bypass geo‑deferral, matching findings that some critical messages must preempt context-based suppression.[^12][^13]
- Expose a UI that shows pending versus delivered items with timestamps and explains why an item was deferred, aligning with transparency recommendations from notification‑management research.[^17][^13]
## 3. Wrong‑Way Driver Detection Beyond Ramps
### 3.1 Safety motivation and traditional systems
Wrong‑way driving—vehicles traveling against traffic on divided highways, ramps, or urban one‑ways—is a high‑risk event leading to severe head‑on crashes, so transportation agencies invest heavily in early detection and driver warning systems.[^22][^23][^24]
Conventional deployments focus on freeway exit ramps and use technologies such as radar, inductive loops, magnetic sensors, thermal and optical cameras, and microwave detectors to detect vehicles entering in the wrong direction, trigger flashing “WRONG WAY” signs, and alert traffic management centers.[^23][^24][^25]
A multi‑technology proof-of-concept for wrong‑way detection evaluated microwave sensors, Doppler radar, video imaging, thermal sensors, and magnetic detectors on freeway ramps and documented controlled tests and real incidents over several months.[^25]
### 3.2 Video‑based wrong‑way detection via motion orientation
A framework proposed for highway operators uses optical‑flow analysis over camera footage to learn the dominant orientation of normal traffic in each lane, modeling the distribution of motion vectors with a Gaussian mixture.[^26]
In the operational phase, the system computes optical flow for new frames and flags objects whose motion direction significantly deviates from the learned lane orientation as potential wrong‑way vehicles, then validates detections temporally to reduce false alarms.[^26]
Field deployments on selected highway segments demonstrate that such models can detect wrong‑way vehicles with high reliability in real traffic while remaining resilient to noise and illumination changes.[^26]
### 3.3 Commercial AI‑based detection solutions
Recent intelligent transportation systems increasingly rely on AI vision cameras that combine object detection, tracking, and direction analytics directly at the edge.[^22][^23][^24]
Vendors describe pipelines where cameras or radar units continuously monitor ramps or segments, apply AI models to track each vehicle’s motion vector, and trigger alerts when motion opposes the defined traffic flow, often validating detections with multi‑sensor fusion (e.g., radar plus thermal and optical cameras) to minimize false positives.[^23][^24][^22]
These products typically integrate with traffic management systems to send event packages containing images, video clips, and metadata, providing design references for alert workflows and operator dashboards.[^24][^23]
### 3.4 Connected‑vehicle wrong‑way concepts
Conceptual designs for connected‑vehicle wrong‑way detection envision vehicles and infrastructure exchanging messages so that a wrong‑way entry can be quickly broadcast to nearby road users and back‑end systems.[^27]
Such designs often combine on‑board sensors, roadside units, and back‑office analytics to detect wrong‑way behavior, issue in‑vehicle warnings, and support dynamic response strategies.[^27]
This line of work suggests how a hackathon project could simulate multi‑vehicle GPS traces or vehicle‑to‑infrastructure messages rather than relying solely on roadside cameras.
### 3.5 Map‑based identification of inconsistent travel direction
Projects leveraging GPS traces and OSM data have developed tools to detect missing or incorrect one‑way tags by analyzing the directionality of matched GPS tracks and comparing it to mapped road attributes.[^28][^29]
If more than a high threshold of matched tracks on an OSM way share the same direction, the tool infers that the segment is one‑way and flags inconsistencies between inferred and mapped directionality.[^28]
This methodology can be repurposed for wrong‑way detection: by inferring each road segment’s allowed travel direction from crowd traces or OSM tags and comparing it against live or simulated multi‑vehicle GPS headings, you can flag vehicles moving against the inferred flow.
### 3.6 Prototype design implications
Based on prior work, a feasible wrong‑way detection‑beyond‑ramps prototype could:

- Use OSM to obtain road geometry and permitted directions, leveraging existing work on one‑way detection and directionality correction to validate or augment tags.[^28][^9]
- Simulate multi‑vehicle GPS traces on an urban grid or campus road network and inject wrong‑way trajectories, then perform map‑matching and heading comparison (vehicle bearing versus edge direction) to flag anomalies, analogous to traffic‑flow analysis tools.[^10]
- Optionally integrate simple camera‑based visualization (e.g., drawing direction arrows on a video feed) inspired by optical‑flow‑based systems, without needing heavy production‑grade computer vision.[^26][^22]
- Present a visual playback highlighting normal versus wrong‑way vehicles and log event details for later analysis, similar to commercial WWVDS event packages but in a simplified research UI.[^23][^25]
## 4. Cross‑cutting Opportunities for a Unified Project
### 4.1 Shared data foundations
All three proposals can share a common spatial foundation based on OSM roads, map‑matching of (real or simulated) GPS traces, and optionally crowdsourced cellular measurements or public coverage datasets.[^1][^9][^2]
This enables reusing route connectivity scores and coverage heatmaps both for cellular‑aware routing and for defining high‑coverage zones that geo‑deferred notifications should target.[^2][^3][^1]
The same road‑segment representation and map‑matching logic can also be used to interpret vehicle headings for wrong‑way detection, so investing in a clean geospatial pipeline pays off across all ideas.[^28][^10]
### 4.2 Combined user experience concepts
A compelling hackathon demo could integrate these strands into a single connected‑mobility dashboard:

- A route planner that shows both ETA and connectivity score, lets users toggle “prefer coverage,” and overlays coverage heatmaps.
- A notification pane that queues non‑urgent messages and visually releases them when the simulated vehicle enters high‑coverage segments, with explanations derived from context‑aware notification research.[^13][^17]
- A safety monitor that replays trips, flagging wrong‑way segments on both highways and campus‑like grids using heading‑versus‑road‑direction logic, and optionally overlaying camera‑style animations inspired by optical‑flow systems.[^26][^22]
### 4.3 Research directions for extension
If extended beyond a hackathon, existing literature suggests further avenues such as learning personalized notification policies from user data, refining connectivity models with 5G positioning and more advanced coverage inference, or incorporating real‑time V2X messages into wrong‑way detection and warning mechanisms.[^8][^17][^27]
These directions align well with current industry interest in intelligent transportation systems and context‑aware mobile services, making the hackathon prototypes natural stepping stones toward publishable work.

---

## References

1. [Connectivity-optimal Shortest Paths Using Crowdsourced ...](https://www.diva-portal.org/smash/get/diva2:974387/FULLTEXT03)

2. [Connectivity-optimal Shortest Paths Using Crowdsourced ...](https://www.ida.liu.se/labs/rtslab/publications/2016/HultmanEtAl_CASPer2016_final.pdf) - by T Hultman · Cited by 8 — The Connectivity-Aware Route Planner (CARP) tool in- tegrates map data f...

3. [How Crowdsourcing Helps You Find Network Issues ...](https://www.rantcell.com/how-crowdsourcing-helps-find-network-issues-with-zero-budget.html) - This crowd-sourced approach helps network operators pinpoint and rectify coverage gaps and connectiv...

4. [Methodology: Mobile Network Benchmark Report](https://www.weplananalytics.com/en/methodology/mobile-quality) - First AI Powered Crowdsourced Analytics in the market. Explore our solutions for Operators, Telecom ...

5. [Mobile Coverage Analysis using Crowdsourced Data](https://arxiv.org/pdf/2510.13459.pdf) - The core of our methodology involves coverage analysis at the individual cell (antenna) level, subse...

6. [Network coverage maps](https://www.gsma.com/coverage/) - This global raster dataset visually represents mobile network coverage, offering an accurate and up-...

7. [Global Coverage Maps](https://www.gsmaintelligence.com/mobile-network-coverage-data) - GSMA Intelligence provides authoritative and comprehensive mobile network coverage data sourced dire...

8. [A feasibility study of 5G positioning with current cellular ...](https://www.nature.com/articles/s41598-023-42426-1) - by B Camajori Tedeschini · 2023 · Cited by 43 — This research examines the feasibility of using sync...

9. [Identifying Roads Uniquely and Traffic API](https://help.openstreetmap.org/questions/43370/identifying-roads-uniquely-and-traffic-api/)

10. [Map Matching When the Map is Wrong](https://www.youtube.com/watch?v=AxZTEtSO0-Q)

11. [Zero-Shot Cellular Trajectory Map Matching](https://arxiv.org/html/2508.06674v1)

12. [[PDF] Using context-aware notification to improve effectiveness of a mobile ...](https://people.cs.vt.edu/~mccricks/papers/Streefkerk_IJMHCI12.pdf)

13. [Snooze! Investigating the User-Defined Deferral of Mobile ...](https://interruptions.net/literature/Weber-MobileHCI18.pdf)

14. [Towards attention-aware adaptive notification on smart ...](https://www.sciencedirect.com/science/article/abs/pii/S1574119215001881) - by T Okoshi · 2016 · Cited by 67 — In this study, we installed our Attelia service on each participa...

15. [Push or Delay? Decomposing Smartphone Notification ...](https://interruptions.net/literature/Turner-HBU15.pdf)

16. [Snooze!: investigating the user-defined deferral of mobile ...](https://dl.acm.org/doi/10.1145/3229434.3229436) - We developed an Android app that allows users to snooze mobile notifications for a user-defined amou...

17. [A framework for intelligent mobile notifications](https://etheses.bham.ac.uk/7440/1/Mehrotra17PhD.pdf) - by A MEHROTRA · 2017 · Cited by 6 — Mobile notifications provide a unique mechanism for real-time in...

18. [[PDF] A context-aware Notification Service](https://www.cl.cam.ac.uk/research/dtg/archived/files/publications/public/ek236/poster_lbs_fin_nn.pdf)

19. [Location-Based Push Notifications: How They Work & Best Use Cases](https://clevertap.com/blog/location-based-push-notifications/) - Learn how location-based push notifications work, the triggers behind them, and how brands use geofe...

20. [How Geofence Push Notifications Work: Best Practices & Examples](https://feeds.nextbillion.ai/blog/geofence-push-notification-service) - Learn how geofence push notifications work, from location triggers to best practices. Discover real-...

21. [[PDF] Towards Geo-Context Aware IoT Data Distribution - David Bermbach](https://dbermbach.github.io/publications/2019-isycc.pdf)

22. [How to Ensure Wrong-Way Driving Detection With AI Vision Cameras](https://www.e-consystems.com/blog/camera/applications/how-to-ensure-wrong-way-driving-detection-with-ai-vision-cameras/) - Wrong-way driving remains one of the highest-risk events on highways and ramps, driven by impaired d...

23. [Wrong Way Vehicle Detection, Warning and Alert System | WW400](https://carmanah.com/product/ww400-wrong-way-vehicle-detection-warning-and-alert-system/) - The WW400 detects wrong-way drivers on highway off-ramps, warns them of their error with high-intens...

24. [5 Must-Know Wrong Way Vehicle Detection Systems for Safety](https://govcomm.us/wrong-way-vehicle-detection-systems/) - Learn how GovComm's Wrong Way Vehicle Detection Systems use advanced technology to prevent accidents...

25. [[PDF] Wrong-way Vehicle Detection: Proof of Concept - ROSA P](https://rosap.ntl.bts.gov/view/dot/25869/dot_25869_DS1.pdf)

26. [A FRAMEWORK FOR WRONG WAY DRIVER DETECTION ...](https://www.a-to-be.com/wp-content/uploads/2018/11/OpenRoads_BrisaCompleto-280-291.pdf)

27. [[PDF] Conceptual Design of a Connected Vehicle Wrong-Way Driving ...](https://library.ctr.utexas.edu/hostedpdfs/tti/0-6867-1.pdf)

28. [New Telenav tool: Fix missing and wrong one-way streets](https://www.openstreetmap.org/user/mvexel/diary/36209) - Last month, we released the Missing Roads plugin and web tool. This quickly became a popular pastime...

29. [How to improve the accuracy of a way in OSM and reverse its direction](https://www.youtube.com/watch?v=MCf0Yd_HPs8) - In this video we will show how to improve the geometry of a way that has been mapped without enough ...

