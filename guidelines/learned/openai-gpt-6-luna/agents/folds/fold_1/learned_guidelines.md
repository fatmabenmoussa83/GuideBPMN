# Learned guidelines: GPT-6 Luna, Reuse training, round 1 (44 descriptions)

82 generic and 3 example-specific error-driven guidelines; 37 generic guidelines confirmed. Full records (evidence, confirmation tests, provenance): `learned_guidelines.json`.

## Generic guidelines

**LRN-005** (T6; refines FID-03; 10 description(s); confirmed: yes)  
When the description names a specific activity and distinguishes it from a related preceding or subsequent activity: Label the BPMN activity with the action stated in the description; do not substitute a related action that the description treats as separate or does not state.

**LRN-032** (T5; refines FID-01; 9 description(s); confirmed: yes)  
When the description states that an activity or decision outcome leads to another activity or a terminal outcome, including on a conditional branch: Model sequence flows connecting the stated nodes in the described order, preserving each described branch through its next activity or terminal outcome.

**LRN-036** (T6; refines FID-03; 9 description(s); confirmed: yes)  
When the description distinguishes related actions, events, or outcomes that could otherwise be confused: Label each BPMN element so the stated distinctions remain clear; do not substitute a related action or use a generic label that could refer to multiple described actions or outcomes.

**LRN-017** (T5; refines EVT-01; 8 description(s); confirmed: yes)  
When the description states that a participant performs a distinct action to initiate the process: Model a start event for the process trigger, followed by a task for the initiating action; do not use the start event to represent the action itself.

**LRN-046** (T6; refines FID-03; 8 description(s); confirmed: yes)  
When the description states an action or decision represented by a BPMN element, including any applicable scope or criteria: Label the element with concise wording that faithfully reflects the stated action or decision and preserves any applicable scope or criteria, without implying unsupported meaning or broader applicability.

**LRN-008** (T5; refines FID-01; 7 description(s); confirmed: yes)  
When the description presents activities or events in a chronological sequence, including how the process begins: Connect the corresponding BPMN elements with sequence flows in the stated order, including a flow from the start event to the first activity and flows between successive activities.

**LRN-061** (T6; refines FID-03; 7 description(s); confirmed: yes)  
When the description states an activity or decision with a particular action, condition, scope, or criterion: Label the corresponding BPMN activity or gateway concisely and faithfully, preserving distinctions relevant to the described action or decision rather than substituting unrelated meaning.

**LRN-004** (T5; refines GW-04; 6 description(s); confirmed: yes)  
When When a description names multiple distinct activities within one phase and states that the process continues only after every activity is finished,: model the activities as parallel branches with a parallel split and join, rather than as a sequence.

**LRN-040** (T5; refines FID-01; 6 description(s); confirmed: yes)  
When the description states that one activity, event, or event outcome leads to another, including after a wait or along an alternative event path: Model sequence flows connecting the corresponding BPMN nodes in the described order, preserving transitions into and out of waiting events and each described alternative path.

**LRN-025** (T6; refines FID-03; 5 description(s); confirmed: yes)  
When the description states a meaningful object, recipient, or responsible role for an activity: Use a concise BPMN label that preserves the described action and those details when they distinguish or clarify the activity.

**LRN-030** (T5; refines ACT-07; 5 description(s); confirmed: no)  
When the description says that independent activities proceed while other work is underway and that a later activity depends on all of them being complete: Model the concurrent activities with a parallel split, then synchronize all required branches with a parallel join before the dependent activity.

**LRN-002** (T6; refines FID-01; 4 description(s); confirmed: yes)  
When the description explicitly states the outcome that terminates the process: Label the end event to reflect that stated outcome; do not use an unstated or different outcome.

**LRN-033** (T6; refines FID-03; 4 description(s); confirmed: no)  
When the description states a decision with distinct outcomes or a time-based condition that triggers an action;: Label the corresponding gateway or event with concise wording that faithfully identifies the described decision or trigger, preserving the distinction relevant to its outcomes.

**LRN-016** (T5; refines GW-01; 3 description(s); confirmed: no)  
When the description states that a process can end with one of several mutually exclusive outcomes: Model the choice with an exclusive gateway and connect each outgoing branch to the activity or end event corresponding to that outcome.

**LRN-021** (T6; refines FID-03; 3 description(s); confirmed: no)  
When the description explicitly states what triggers the process or what outcome terminates it: Label the corresponding start or end event with a concise, faithful description of that stated trigger or outcome rather than a generic label.

**LRN-006** (T5; refines FID-01; 2 description(s); confirmed: yes)  
When the description says an activity may take place before a later activity: Model the optional activity as a decision branch with a path that bypasses it; merge the paths before the later activity.

**LRN-009** (T6; refines FID-03; 2 description(s); confirmed: yes)  
When the description states an activity and provides criteria or other supporting details that are not needed to identify that activity: Label the BPMN element with a concise name for the stated action; omit supporting details that do not distinguish it from another modeled activity, while preserving details that are themselves distinct actions or alternatives.

**LRN-010** (T5; refines FID-01; 2 description(s); confirmed: no)  
When the description states that named activities may be performed as optional additions to the main sequence: Model each named activity in the optional flow, using gateways to reflect whether the activities are alternatives or whether one or more may occur.

**LRN-012** (T5; refines FID-02; 2 description(s); confirmed: no)  
When the description states that information is recorded in a system before a subsequent handling action: Model the recording as a distinct activity and connect it in sequence before that handling action.

**LRN-013** (T6; refines FID-03; 2 description(s); confirmed: yes)  
When the description explicitly states the object or scope of an activity: Retain that meaningful object or scope in the BPMN task label while keeping the label concise.

**LRN-015** (T6; new; 2 description(s); confirmed: no)  
When the description explicitly lists multiple objectives or criteria that an activity is meant to address: Preserve the stated objectives or criteria in the BPMN task label rather than narrowing the label to only one of them.

**LRN-020** (T5; refines ACT-07; 2 description(s); confirmed: no)  
When the description states that an ongoing activity continues while a separate review or decision proceeds: model the activities as concurrent paths with a parallel gateway, and synchronize them before any later step that depends on both paths being complete

**LRN-028** (T5; refines FID-01; 2 description(s); confirmed: yes)  
When the description states that a participant performs a distinct activity after a condition is met: Model the activity as a BPMN task and connect it to the surrounding process flow.

**LRN-031** (T6; refines FID-03; 2 description(s); confirmed: yes)  
When the description explicitly identifies the role or participant responsible for an activity: Include the stated performer in the activity label when it would otherwise be omitted, while keeping the label concise and faithful to the described action.

**LRN-034** (T7; refines COL-01; 2 description(s); confirmed: no)  
When the description mentions an external person or organization as the recipient of a request, the source of a response or payment, or the destination of a referral, but does not describe that party’s own process or responsibilities: model the stated work and events within the modeled participant; do not create separate participant pools or message flows solely because of that mention

**LRN-039** (T7; refines COL-04; 2 description(s); confirmed: yes)  
When the description distinguishes multiple communications between participants, such as an initial request and a separate response or status update: Model each stated communication as its own message flow to the corresponding receiving interaction.

**LRN-047** (T6; refines FID-01; 2 description(s); confirmed: no)  
When the description says that a person selects an option and that subsequent actions depend on which option was selected: Model the selection as an activity, then use a gateway to route the resulting alternatives.

**LRN-049** (T6; new; 2 description(s); confirmed: no)  
When the description states that a participant selects or performs an action, rather than deciding whether a condition holds: Model the stated action as an activity and label it with that action; use a gateway for the condition-based decision, labeling it to preserve the distinction.

**LRN-056** (T5; refines FID-01; 2 description(s); confirmed: yes)  
When the description states distinct activities or decisions within a workflow, along with outcomes or dependencies between them: Model those activities and decisions as explicit elements at the process level needed to preserve the stated sequence, branches, and synchronization; do not collapse them into a generic subprocess that obscures that structure.

**LRN-067** (T5; refines GW-01; 2 description(s); confirmed: no)  
When the description states that the outcome of an evaluation determines whether further activities are required: Model an exclusive gateway after the activity that evaluates the outcome, with branches for whether the further activities are required.

**LRN-072** (T5; new; 2 description(s); confirmed: yes)  
When the description states that a participant performs an explicit check before a separate decision determines whether a loop continues or ends: Model the check as an activity, followed by a gateway that represents the condition-based decision.

**LRN-001** (T5; refines EVT-01; 1 description(s); confirmed: no)  
When the description states that the process begins when an incoming communication or request occurs, without describing separate work to receive it: Represent that occurrence with a suitable start event; model a separate receipt activity only when the description states that receiving it is work to be performed.

**LRN-003** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states distinct decisions or approvals at different points in the process: Model each decision or approval at the point stated, and connect it to the activities that precede and follow it in the described order; do not replace one decision with another.

**LRN-007** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that an item may be put away in one of multiple alternative locations: Model each alternative destination as a separate activity on a mutually exclusive branch, distinct from other stated handling activities.

**LRN-011** (T6; new; 1 description(s); confirmed: yes)  
When the description states that an artifact or information is sent from one participant to another and specifies a communication channel: Label the modeled sending activity from the responsible sender’s perspective and include the specified channel in its label.

**LRN-014** (T5; refines GW-03; 1 description(s); confirmed: yes)  
When the description states that an implementation can take one of several alternative forms: Model each form as a separate activity on mutually exclusive branches, then merge the branches before the next common activity.

**LRN-018** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that a later activity occurs only after an earlier activity succeeds: Model the success outcome as a decision and connect its success path to the dependent activity in the stated order; preserve any other stated outcome paths.

**LRN-019** (T5; refines ACT-07; 1 description(s); confirmed: yes)  
When the description says a later activity occurs after an earlier activity succeeds but does not describe an alternative outcome or failure handling: Model the stated sequence with a direct sequence flow; do not add a decision gateway solely to represent an unspecified failure path.

**LRN-022** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description explicitly includes a change to resources, terms, or entitlements as part of completing an outcome: Model that change as an activity in the outcome’s completion path.

**LRN-023** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description distinguishes preparatory work from a subsequent examination and states that findings are identified after the examination: model the examination as a distinct activity before the activity that identifies its findings

**LRN-024** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says an authorized person may approve an item, and later work proceeds only if it is approved: Model the approval as a distinct activity on the approved path, separate from the gateway that represents the approval decision, and connect it to the subsequent work.

**LRN-026** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description names an overall activity and separately describes constituent work or a conditional path within that activity: Model the named overall activity as a task in addition to representing the constituent work or conditional path when these are also described; do not let the latter replace the named activity.

**LRN-027** (T6; refines QA-04; 1 description(s); confirmed: no)  
When the description states multiple possible actions or outcomes for a single activity: Label the corresponding BPMN activity so that each explicitly stated alternative remains visible; do not use a narrower label that omits one.

**LRN-029** (T5; new; 1 description(s); confirmed: yes)  
When the description states that an optional repeat action causes a later activity to occur again after it has already occurred on the normal route: Model the normal route and the repeat route as converging through an explicit merge gateway before the later activity.

**LRN-035** (T7; refines COL-01; 1 description(s); confirmed: yes)  
When the description narrates process work in the first person, with the speaker performing the described activities but not explicitly naming that speaker as a participant: Model the speaker as a BPMN participant pool and place the narrated activities in that participant’s process.

**LRN-037** (T7; refines COL-01; 1 description(s); confirmed: yes)  
When the description identifies a user-facing software interface as the channel through which a process is initiated and its status or outcomes are delivered: Model that interface as a separate participant pool and represent the interactions with message flows.

**LRN-038** (T5; refines EVT-03; 1 description(s); confirmed: no)  
When the description states that a requested outcome may arrive through either a prompt response or a response preceded by a separate delay notice: Model the alternatives as explicit response paths, with a decision point and distinct handling for the delay notice and the eventual outcome.

**LRN-041** (T6; new; 1 description(s); confirmed: yes)  
When the description states communication between participants and distinguishes the sender from the recipient: Label each communication activity from the perspective of its modeled performer, preserving whether that participant sends or receives information and who the counterpart is; do not reverse the communication direction.

**LRN-042** (T5; refines GW-07; 1 description(s); confirmed: yes)  
When the description distinguishes a notification from a later recipient response or arrival, and says a subsequent action depends on that later occurrence: Model the response or arrival as the catching event that enables the subsequent action; do not use the notification itself as a substitute for that occurrence.

**LRN-043** (T7; refines EVT-04; 1 description(s); confirmed: yes)  
When the description states that one participant communicates with another participant or transfers an item to them: Model the message flow between elements that represent the described sender and receiver. Use a receiving event as an endpoint only when it represents receipt of that communication; do not substitute an unrelated activity or event for either endpoint.

**LRN-044** (T7; refines ACT-05; 1 description(s); confirmed: no)  
When the description states that one participant communicates information to another participant and separately describes the recipient’s later reaction, arrival, or other action: Model the communication with a message flow from the sending participant’s communication element to an element that represents receipt of that communication; model the recipient’s later reaction or action separately in that participant’s process.

**LRN-045** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description states that a notification may concern different categories or severity levels, and that follow-up obligations depend on which category or level applies: model a decision gateway after the notification, with conditional branches to the applicable follow-up actions

**LRN-048** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description presents multiple distinct data fields or selections as separate actions: Model each stated entry or selection as its own activity, preserving the described order and dependencies.

**LRN-050** (T5; refines ACT-02; 1 description(s); confirmed: no)  
When the description says that a participant must identify or choose inputs that will guide later work: Model that human selection as a user task before the work that uses those inputs.

**LRN-051** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description states that a prerequisite may need to be completed before other work can proceed: Model a gateway at the point where the prerequisite is assessed, with branches for completing the prerequisite and proceeding without it when it is not needed.

**LRN-052** (T7; refines LANE-01; 1 description(s); confirmed: yes)  
When the description assigns activities in one end-to-end process to both a human and an automated system: Model their responsibilities in separate lanes of the same process; use separate participant pools only when the description presents them as independent communicating participants.

**LRN-053** (T5; refines EVT-03; 1 description(s); confirmed: no)  
When the description says that a participant sends status updates while an activity is in progress: model each update as an intermediate message catch event in the process flow, rather than as a task, a separate subprocess, or start/end events.

**LRN-054** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description states a desire, need, or other condition that prompts a subsequent activity: Label the start event with that initiating condition rather than naming the activity that follows.

**LRN-055** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description says that several constituent items are processed through separate paths and that a later activity depends on all paths reaching a specified outcome: Model the required synchronization before evaluating the collective condition, then connect the qualifying outcome to the dependent activity and preserve any alternative outcomes.

**LRN-057** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description makes a later activity contingent on whether an earlier result is approved or accepted: Model the decision with an exclusive gateway and a conditional sequence flow for the stated approval outcome; do not add an unstated outcome.

**LRN-058** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description gives timing, manner, or broader workflow context for an activity without making that context part of the activity itself: Name the BPMN task with its essential action and object; do not append contextual details that are already conveyed by the process flow or do not distinguish the activity. Represent meaningful timing, repetition, or parallelism in the BPMN structure when applicable.

**LRN-059** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description says to contact multiple external providers and obtain specified information from them before using it to make a choice: Model obtaining that information as a distinct activity after the contact and before the choice.

**LRN-060** (T5; refines SUB-05; 1 description(s); confirmed: no)  
When the description requires checking or collecting information for every member of a set before acting on the set as a whole: Model the per-member work as an explicit repetition, use a decision to repeat while members remain, and route completion of the repetition to the collective follow-up activity.

**LRN-062** (T5; refines GW-01; 1 description(s); confirmed: no)  
When the description states that whether one provider can meet a requirement determines whether one or multiple providers are used: Model the alternatives with an exclusive gateway, and condition its outgoing flows on the stated requirement.

**LRN-063** (T7; refines COL-01; 1 description(s); confirmed: no)  
When the description identifies an external participant as receiving a request or information and explicitly states that the participant responds or processes it: model the external participant as a separate pool and represent the stated exchanges with message flows between appropriate communication and receipt elements

**LRN-064** (T5; refines FID-01; 1 description(s); confirmed: no)  
When When the description states that prepared items are ordered: Model ordering as a distinct activity after the preparation activity, with a sequence flow connecting them.

**LRN-065** (T5; refines PROC-05; 1 description(s); confirmed: no)  
When the description says that work in an ongoing process resumes after a later trigger: model the trigger within the existing process and represent the stated continuation as an activity, rather than as a new process start

**LRN-066** (T6; refines FID-04; 1 description(s); confirmed: no)  
When the description specifies a threshold-based condition but does not state its numeric cutoff: Label the corresponding gateway with the stated condition without adding an unsupported numeric cutoff.

**LRN-068** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says a participant will arrive at an unspecified time and subsequent work depends on that arrival: model the wait for the arrival as an intermediate catch event, not as an event-based gateway waiting for a different outcome

**LRN-069** (T5; new; 1 description(s); confirmed: yes)  
When the description states that a process waits for a later occurrence before the next activity can begin: Model the wait as an intermediate catch event for the described occurrence, placed between the preceding activity and the activity that follows it.

**LRN-070** (T6; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that a consequence is imposed after a deadline if a required action has not occurred: Model imposing the consequence as a BPMN task, and represent the deadline and unmet-action condition with appropriate event and flow logic; do not use an end event to represent the consequence itself.

**LRN-071** (T1; refines XML-03; 1 description(s); confirmed: no)  
When the description requires a BPMN model to be serialized as XML: Assign every BPMN element an ID that conforms to XML ID syntax (NCName) and is unique within the document.

**LRN-073** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description states that a later activity can occur only after multiple independent activities or steps have all been completed: Model the required paths as parallel branches and join them with a parallel gateway before the later activity.

**LRN-074** (T5; refines FLOW-06; 1 description(s); confirmed: yes)  
When the description gives alternative outcomes for handling an individual item, followed by a check of the larger set and a decision about whether to continue processing items: Connect each alternative outcome path to the shared check. Model an explicitly described check as an activity before a condition-based gateway, and route the gateway’s outcomes to the described continuation or completion paths.

**LRN-075** (T5; refines ACT-07; 1 description(s); confirmed: yes)  
When the description makes a later action conditional on whether a completed wait exceeded a stated duration: Model the condition with a decision gateway after the wait, route the conditional action on the appropriate branch, and rejoin the paths before the next common activity.

**LRN-076** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description provides a process title but does not state an explicit start trigger: label the start event with the process title rather than a generic label

**LRN-077** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description states an activity or decision with a specific action, object, or criterion that distinguishes it from related actions or decisions: Label the corresponding BPMN element concisely while preserving that stated meaning and any distinction needed to identify it.

**LRN-078** (T6; refines FID-01; 1 description(s); confirmed: yes)  
When the description says that work continues beyond a decision outcome: Model the stated continuation as an activity in the process rather than treating it as a process end.

**LRN-079** (T6; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that work is reviewed and may be accepted or rejected, with rejected work returned for revision: Model the review as a distinct activity, the accept-or-reject decision as an exclusive gateway with labeled outcome branches, and the rejection path as a loop back to the activity that produced the work.

**LRN-080** (T6; refines FID-02; 1 description(s); confirmed: no)  
When the description distinguishes an item being submitted or provided from its subsequent registration or recording: Model submission and registration as separate activities, preserving their stated order.

**LRN-081** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that a participant performs a distinct action after checking or examining something: Model the action as a separate BPMN task and connect it in sequence after the check.

**LRN-082** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a participant responds to a request based on the result of a check: Model the response as a separate BPMN task after the check, and represent any stated alternative response outcomes in the process.

## Example-specific guidelines

**EXS-003** (T5; refines ACT-05; 1 description(s); confirmed: no)  
When the description says that a participant receives a notification and then communicates to a person that they should take a later follow-up action: Model receipt of the notification as an appropriate message event, and model the communication to the person as a separate user task.

**EXS-008** (T5; new; 1 description(s); confirmed: no)  
When the description assigns follow-up reporting duties according to an event’s type or severity, or a person’s coverage, and states that some duties apply independently of other duties: Model each stated distinction with decision gateways and route every applicable reporting duty along its own branch; keep duties that apply independently separately reachable so they can be performed as well.

**EXS-009** (T6; new; 1 description(s); confirmed: no)  
When the description limits an activity or decision to a specified actor, triggering event, eligibility criterion, or time window: Label the corresponding BPMN activity or decision so its wording preserves the applicable scope and criteria, distinguishing it from related actions or decisions without making it appear to apply more broadly.
