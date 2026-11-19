# Learned guidelines: GPT-6 Luna, Reuse training, round 4 (44 descriptions)

88 generic and 3 example-specific error-driven guidelines; 37 generic guidelines confirmed. Full records (evidence, confirmation tests, provenance): `learned_guidelines.json`.

## Generic guidelines

**LRN-015** (T6; refines FID-03; 24 description(s); confirmed: yes)  
When the description states the action, purpose, recipient, scope, or outcome of a process element: Label the corresponding BPMN element with a concise phrase that preserves those stated semantics; do not substitute a related but different meaning, omit distinguishing details, or add unsupported details.

**LRN-009** (T5; refines FID-01; 8 description(s); confirmed: yes)  
When the description explicitly states that an actor performs an action that initiates the described process: Model the stated action as an activity in the actor’s scope; do not use a start event representing the resulting occurrence as a substitute for that activity. Represent the process start separately with an appropriate start event.

**LRN-003** (T5; refines ACT-07; 7 description(s); confirmed: yes)  
When the description says that one of several alternatives is selected, or that an activity may occur: Model the choice or optional activity with an appropriate gateway, and reconnect the resulting paths before subsequent common work.

**LRN-024** (T6; refines FID-03; 7 description(s); confirmed: yes)  
When the description states an activity's object, scope, or alternative actions: Label the corresponding BPMN task concisely, preserving the stated action and distinctions without substituting a related action or adding unsupported meaning.

**LRN-026** (T5; refines FLOW-01; 7 description(s); confirmed: yes)  
When the description explicitly states that an activity follows the process start or another activity: connect the corresponding BPMN elements with sequence flows in the stated order, preserving any intervening gateways and branches

**LRN-004** (T6; refines FID-01; 6 description(s); confirmed: no)  
When the description names an activity or milestone for which a BPMN task is being labeled: Label the task to preserve the action and purpose stated in the description; do not substitute a related but different action or milestone.

**LRN-037** (T6; refines FID-03; 6 description(s); confirmed: yes)  
When the description distinguishes multiple activities or events by their action, information, or outcome: Label each corresponding BPMN element to preserve those distinctions, rather than using interchangeable or overly generic labels.

**LRN-010** (T6; refines FID-03; 5 description(s); confirmed: yes)  
When the description explicitly specifies multiple actions, a recipient, or a distinguishing object or scope for an activity: Label the BPMN task to preserve those stated semantic details when they clarify what is done; do not omit or alter them, or add unsupported details.

**LRN-023** (T5; refines ACT-07; 5 description(s); confirmed: yes)  
When the description states that work proceeds concurrently and that a later step must wait until all of that work is complete: Model the concurrent work as parallel branches and synchronize them with a parallel gateway before the dependent step.

**LRN-005** (T5; refines GW-04; 4 description(s); confirmed: yes)  
When the description names multiple required activities in a phase, gives no order among them, and states that a later outcome occurs only after the phase is finished: Model each activity separately, use a parallel split for the unordered activities, and join their branches before modeling the later outcome.

**LRN-002** (T6; refines FID-04; 3 description(s); confirmed: yes)  
When the description states a condition that determines whether a path continues but does not state what happens when it does not: Use a neutral label for any modeled end event on that path rather than asserting an unsupported outcome.

**LRN-007** (T5; refines FID-01; 3 description(s); confirmed: yes)  
When the description states that an actor identifies or determines a need before subsequent work begins: Model the identification as a task after a start event; do not represent the stated action only as the start event.

**LRN-001** (T5; refines FID-01; 2 description(s); confirmed: no)  
When the description makes an activity contingent on whether a stated condition holds: Model the condition with an exclusive gateway at the point where it affects the flow, and route the contingent activity only along the branch where the condition holds. Do not invent an outcome for the other branch.

**LRN-006** (T6; refines FID-03; 2 description(s); confirmed: no)  
When the description establishes an overarching subject or context that applies to several separately stated activities: Label each task with its stated action and purpose, omitting repeated context and qualifiers unless needed to distinguish the activity; do not add unsupported details.

**LRN-012** (T6; refines FID-03; 2 description(s); confirmed: no)  
When the description explicitly states the outcome that ends the process: Label the BPMN end event with a concise phrase that preserves that stated outcome rather than using a generic label.

**LRN-013** (T5; refines FID-02; 2 description(s); confirmed: no)  
When the description lists multiple distinct evaluation objectives within an assessment: Model each objective as a separate BPMN activity rather than combining them into one activity.

**LRN-030** (T5; refines GW-06; 2 description(s); confirmed: yes)  
When the description distinguishes mutually exclusive cases by conditions, assigns different actions to them, and later gives them a shared continuation: Model the case selection with an exclusive split, and reconverge the alternative paths with an exclusive merge before the shared continuation.

**LRN-045** (T6; refines FID-03; 2 description(s); confirmed: yes)  
When the description explicitly assigns an activity to an actor or states who sends or receives something: Make the stated performer and the direction of the interaction clear in the BPMN activity labels; do not reverse who performs, sends, or receives the action.

**LRN-046** (T5; refines GW-04; 2 description(s); confirmed: no)  
When the description requires multiple distinct activities and states no order or dependency between them: Model the activities as branches from a parallel gateway so that all branches can proceed.

**LRN-050** (T5; refines GW-01; 2 description(s); confirmed: no)  
When the description says that work can branch into parallel or conditional activities, or that a setback returns the process to earlier work: Connect the affected activities with sequence flows, using gateways to represent the described branching or synchronization and preserving any stated return flow.

**LRN-053** (T5; refines FID-02; 2 description(s); confirmed: no)  
When the description explicitly states that activities can happen in parallel or that one activity occurs during another activity: Model those activities as concurrent branches and preserve their stated dependencies and order; do not impose a sequential order that the description does not require.

**LRN-058** (T5; refines ACT-08; 2 description(s); confirmed: no)  
When the description states that software automatically produces or presents information for a person: Model the software’s provision of that information as a service task, rather than modeling the person’s receipt of it as a user task.

**LRN-075** (T6; refines FID-03; 2 description(s); confirmed: no)  
When the description identifies an activity, decision, or outcome by its action or purpose: label the corresponding BPMN element to preserve that stated meaning, rather than substituting a related but different action or outcome

**LRN-078** (T6; refines FID-01; 2 description(s); confirmed: no)  
When the description states that one activity is completed before a different activity begins: Model each stated activity as its own activity in the stated order; do not use one activity as a substitute for another.

**LRN-008** (T6; refines FID-03; 1 description(s); confirmed: yes)  
When the description states an activity and separately specifies criteria used to perform it: Label the activity with its concise core action; do not add the criteria to the activity label unless they are needed to distinguish it from another activity.

**LRN-011** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description states that information is reported or submitted and separately says it is later entered or recorded in a system: Model the reporting or submission and the later system-recording work as separate BPMN elements; do not treat the initial report as completing the recording activity.

**LRN-014** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description explicitly identifies a substantive verification as part of a broader review: Model the verification as a BPMN activity rather than leaving it implicit in the broader review.

**LRN-016** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description says that a decision or outcome is communicated to a person: Model the communication as a distinct activity; do not treat the decision gateway itself as the communication.

**LRN-017** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description says an optional activity may occur after a case reaches its completion, regardless of which outcome completed the case: Model the optional activity as a subsequent activity reached from the applicable completion paths, rather than as a new process start event.

**LRN-018** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says that work may be revised in response to feedback from repeated evaluation cycles before a final decision: Model feedback and revision as distinct activities, and use a loop that repeats evaluation and revision until the stated acceptance condition is met.

**LRN-019** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states a review activity and separately identifies the findings produced by that review: Model the review and the identification of its findings as separate tasks, with the review before the findings-identification task.

**LRN-020** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that a distinct body of work is started and also describes the work performed within it: Model the stated act of starting the work as a separate activity before the workflow that performs it; do not use that workflow, a subprocess, or a start event as a substitute for the activity.

**LRN-021** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that approval is followed by required activities and that the process closes after those activities: Connect the approval outcome through all required follow-up activities to the process end, preserving any ordering or parallelism stated in the description.

**LRN-022** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description names an action and then describes work it comprises, without identifying a distinct process scope or an independent trigger for that work: Model the named action as an activity in the current process, and represent the constituent work at the level of detail stated. Do not replace the action with a subprocess and its own start and end events solely because the description lists work it comprises.

**LRN-025** (T6; refines ACT-06; 1 description(s); confirmed: yes)  
When the description explicitly assigns an activity to a role, and the BPMN model does not otherwise make the performer clear: Include the stated role in the activity label along with the action.

**LRN-027** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description states a final activity but does not explicitly identify the outcome that ends the process: Use a generic end-event label rather than inferring a specific business outcome from that activity.

**LRN-028** (T5; refines GW-06; 1 description(s); confirmed: yes)  
When the description states that one activity is required while an independent activity is performed only when a condition holds: Model an inclusive split so the required activity and the conditionally applicable activity can proceed, then use an inclusive join before their shared continuation.

**LRN-029** (T7; refines LANE-01; 1 description(s); confirmed: no)  
When the description explicitly assigns an activity to a role within the process: Place the activity in the lane for the stated performing role, rather than in the lane of the person coordinating the process.

**LRN-031** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description explicitly states that a matter is brought to completion after a decision or another activity: Model the stated completion work as an activity on the applicable path before the process outcome.

**LRN-032** (T7; new; 1 description(s); confirmed: yes)  
When the description mentions an external person or organization only as the recipient or source of a communication, without describing that party performing process activities or a separate process: Model the stated communication and any resulting wait or receipt within the described process; do not add a separate participant pool or message flows for that party.

**LRN-033** (T7; refines COL-01; 1 description(s); confirmed: no)  
When the description narrates work performed by a first-person actor and states that the actor communicates with people or organizations outside that work: Model the narrated actor as a participant pool in the collaboration, with the actor’s described work in its process.

**LRN-034** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that an actor performs a concrete action on a decision outcome or after another activity: Model the stated work as an activity on the applicable path. Use gateways to route or synchronize flow, not as substitutes for the work.

**LRN-035** (T5; refines EVT-03; 1 description(s); confirmed: yes)  
When the description says a participant may send an interim communication before continuing its work and sending a final response: model the interim communication on the applicable conditional path, continue the participant’s subsequent work on that path, and model the other participant’s wait for the final response with a catching event

**LRN-036** (T7; refines COL-01; 1 description(s); confirmed: no)  
When the description distinguishes a user-facing software interface from a backend process and states that users receive results or status updates through that interface: Model the interface as a separate participant pool and represent the described communication between it and the backend with message flows.

**LRN-038** (T7; refines EVT-04; 1 description(s); confirmed: no)  
When the description says an external participant notifies an internal process while continuing its own work: Model the notification as a message flow from the external participant to a receiving message event in the internal process.

**LRN-039** (T3; refines COL-03; 1 description(s); confirmed: no)  
When the description presents one participant's work as following a handoff from another participant: Model the receiving work as connected to that handoff: use sequence flow within the same process, or a message flow to a message-triggered start or catch event in a separate process, rather than an unconnected start-to-end chain.

**LRN-040** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description explicitly states that a participant prepares a physical item for transfer and gives it to another participant, while also describing a later event involving that item: Model the preparation and transfer as activities; do not use the later event involving the item as a substitute for either activity.

**LRN-041** (T7; refines COL-01; 1 description(s); confirmed: yes)  
When the description identifies distinct participants and describes information or items being communicated or handed off between them: Model each participant as a separate pool and represent each described exchange between participants with a message flow from sender to receiver, using valid interaction nodes.

**LRN-042** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description distinguishes preparation for an activity from a period of carrying it out and a later review or decision about continuing it: Model the carrying-out period as a distinct activity in the process flow between the preparation and the later review or decision; do not omit it merely because the description gives few operational details.

**LRN-043** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description says that a participant decides at the end of a stated period whether to continue an activity: Model the decision after that period and use an exclusive gateway to route either to continuation work or to completion.

**LRN-044** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that an event immediately causes an action while other activities may proceed independently: Model the action as triggered directly by that event; do not require unrelated activities to finish before it occurs.

**LRN-047** (T6; new; 1 description(s); confirmed: no)  
When the description says that an action may be required based on a stated condition and also describes a later process outcome: Model and label the decision gateway according to whether that action is required; do not use the later outcome as the gateway’s decision.

**LRN-048** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description identifies two or more distinct objectives or workstreams within one process: Model the described activities and outcomes for each workstream, and do not end the process after completing only one.

**LRN-049** (T5; refines FLOW-07; 1 description(s); confirmed: no)  
When the description says an activity is repeated until a stated condition is met: Model the condition as a decision after the repeated activity; route the unmet outcome back to that activity and the met outcome onward.

**LRN-051** (T7; refines LANE-01; 1 description(s); confirmed: no)  
When the description assigns preparation or configuration work to a human and subsequent execution to an automated system within the same workflow: Represent the human and automated responsibilities in separate lanes, and model an explicitly stated action that starts the automated work as an activity in the system’s lane.

**LRN-052** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description says information must be gathered or choices made before the main work begins: Model the gathering or choice as a distinct activity and connect it before the main work; do not use the main-work workflow as a substitute for it.

**LRN-054** (T5; new; 1 description(s); confirmed: no)  
When the description states that an initial deliverable is sent for customer review, that later work depends on the customer's approval, and that status communications occur during the initial work: Model the status communications alongside the initial work, and represent the customer's review as a decision that gates the later work; connect the approval outcome to that work.

**LRN-055** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that an activity must be completed for every case before a later activity: Keep that required activity on every path to the later activity, and do not add a bypass branch unless the description states an exception.

**LRN-056** (T5; refines FID-02; 1 description(s); confirmed: yes)  
When the description specifies multiple thresholds for the same quantity, with a different action at each threshold, and meeting a lower threshold also meets a higher-threshold condition: Model the conditions so that the lower-threshold condition is evaluated after the higher-threshold condition, preserving both applicable actions when the lower threshold is met.

**LRN-057** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description states explicit criteria for comparing alternatives or thresholds that lead to different actions: Preserve the stated criteria and thresholds in gateway labels or branch conditions, and label each resulting activity with the action the description specifies.

**LRN-059** (T5; refines ACT-02; 1 description(s); confirmed: yes)  
When the description provides directions for a person to perform physical work themselves: model the person's execution as a manual task in sequence after the directions are provided

**LRN-060** (T3; refines EVT-02; 1 description(s); confirmed: no)  
When the description states that the process terminates when a condition occurs: Model that termination path with an end event.

**LRN-061** (T5; refines PROC-05; 1 description(s); confirmed: no)  
When the description states that ongoing work resumes after a later event: Model the event that triggers resumption separately from the activity that resumes, and connect that activity back into the ongoing process.

**LRN-062** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description says that ongoing work should resume after a stated event: Model the event that enables the flow separately from the resumed work, and connect the work after that event; do not use the event alone to represent the work.

**LRN-063** (T6; refines FID-01; 1 description(s); confirmed: yes)  
When the description says that a process collects or retrieves information from a source for a calculation or subsequent work: Model the collection or retrieval as a distinct activity before the information is used.

**LRN-064** (T6; refines FID-04; 1 description(s); confirmed: no)  
When the description states that subsequent activities depend on evaluation findings but does not specify which finding controls the decision: Label the decision point by the stated general dependency rather than naming a particular criterion.

**LRN-065** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description distinguishes an action performed by a person from work performed automatically by a system: Model the human action and the automated system work as separate BPMN activities, using a user task for the human work and a service task for the automated work.

**LRN-066** (T3; refines PROC-05; 1 description(s); confirmed: yes)  
When the description presents an event or activity as a later step in the same process rather than as an independent process trigger: Connect it to the preceding control flow with sequence flow instead of modeling it as a detached start-to-end chain.

**LRN-067** (T6; refines EVT-04; 1 description(s); confirmed: yes)  
When the description assigns a communication to a participant, for example by saying that the participant is notified, receives information, or makes a payment: Model the communication from the stated participant’s perspective and preserve its direction. When receiving the communication affects the process flow, model the recipient side with a catching message event rather than a task that sends it.

**LRN-068** (T5; refines GW-07; 1 description(s); confirmed: yes)  
When the description presents the start of an activity and the elapse of a deadline as competing events after a notification: Model the wait with an event-based gateway leading to a catching event for the activity’s start and a timer event for the deadline, so whichever occurs first selects the path.

**LRN-069** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description specifies an action’s actor, direction, or purpose: Model the stated action from the stated participant’s perspective, preserving its direction and purpose; do not substitute a related communication, data-entry, payment, or scheduling action.

**LRN-070** (T5; refines EVT-04; 1 description(s); confirmed: yes)  
When the description states that a communication or other action recurs at a fixed time interval while work is ongoing: Model the recurring action with a timer event and control flow that allows it to recur during the ongoing work, rather than omitting the timer sequence.

**LRN-071** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says a participant is asked to choose between alternatives and the subsequent process flow depends on that choice: Model obtaining the participant’s choice as an activity before the decision gateway, then use the gateway to route the alternatives.

**LRN-072** (T5; new; 1 description(s); confirmed: yes)  
When the description makes an action depend on whether the time spent waiting for an item to be received exceeded a stated threshold: Model an exclusive gateway after the receipt, routing to the action only when the threshold was exceeded.

**LRN-073** (T6; refines EVT-03; 1 description(s); confirmed: yes)  
When the description states that progress waits for a specified occurrence before distinct work is performed afterward: Model the wait as an intermediate catch event and the later work as a separate activity, labeling each element for the occurrence or work it represents.

**LRN-074** (T5; refines FLOW-06; 1 description(s); confirmed: no)  
When the description explicitly places an outcome at the end, after preceding required work: Model the activity that produces that outcome after the preceding required activities have completed, rather than directly from an earlier concurrent split.

**LRN-076** (T5; refines GW-04; 1 description(s); confirmed: yes)  
When the description lists multiple required operations without specifying their order and states that a distinct follow-up occurs after each operation: Model the operations as required branches from a parallel split, with each follow-up on its corresponding branch.

**LRN-077** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a decision determines whether the process continues or an alternative outcome occurs: Model the decision with an exclusive gateway and provide a separate outgoing flow for each described outcome, connecting each flow to its corresponding next step.

**LRN-079** (T5; refines FID-02; 1 description(s); confirmed: yes)  
When the description states distinct activities leading to a decision, with one outcome returning work for another attempt and another outcome continuing the process: Model the stated activities in their described order, then use a decision gateway to connect each outcome to its corresponding return or continuation path.

**LRN-080** (T6; refines FID-02; 1 description(s); confirmed: no)  
When the description states that one activity is completed before a distinct subsequent activity: Model the activities separately, using an appropriate BPMN element for each, and preserve their stated order rather than letting one element stand for both.

**LRN-081** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description explicitly states that work is checked or reviewed before an outcome is decided: Model the check or review as an activity before the decision, rather than treating the decision alone as representing both actions.

**LRN-082** (T6; refines FID-02; 1 description(s); confirmed: no)  
When the description distinguishes submitting an item from a later registration or recording of that item before another activity: Model submission and registration as separate BPMN activities, preserving their stated order and any stated dependency.

**LRN-083** (T1; refines EVT-14; 1 description(s); confirmed: yes)  
When the description states that an activity or event sends, receives, or waits for a message: Place any message reference in the schema-defined location for the selected BPMN element; do not serialize it as a child element unless the BPMN schema allows it there.

**LRN-084** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states mutually exclusive alternatives as actions performed by a participant: Model each stated action as a task on its own exclusive branch, rather than as a separate end event. If the alternatives have a shared continuation or completion, join them with an exclusive merge before it.

**LRN-085** (T5; refines ACT-05; 1 description(s); confirmed: yes)  
When the description says that a participant sends information to another participant: Model the sending action as a task in the sender’s process, rather than as a send task.

**LRN-086** (T5; new; 1 description(s); confirmed: yes)  
When the description presents activities as successive steps, with one action followed by another in the stated process order: Connect the corresponding activities with sequence flows in that order, and connect the final activity of the process to an end event.

**LRN-087** (T5; refines COL-03; 1 description(s); confirmed: no)  
When the description says one participant sends a request that another participant then acts on: Model receipt of the request as the point that leads into the recipient’s work, rather than starting that work independently. Use a sequence flow when both are in one process; across pools, connect the request by message flow to a receive task or message-triggered start or catch event.

**LRN-088** (T5; refines ACT-07; 1 description(s); confirmed: yes)  
When the description states that one or more conditional outcomes return work to an earlier activity, and the initial route also reaches that activity: Model the initial route and the return flows as converging through an exclusive gateway immediately before the repeated activity.

## Example-specific guidelines

**EXS-014** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description lists specific documents or other requirements that must be met for an application or decision: Model activities to obtain or prepare each listed requirement before the application is submitted or the decision is reached.

**EXS-015** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description asks for one process combining multiple distinct work areas: Model the activities supported for each requested area, and do not end the process after representing only one area while other requested work remains.

**EXS-020** (T5; refines ACT-04; 1 description(s); confirmed: no)  
When the description says that a participant sends material to another participant, receives a result, and may send further feedback before accepting it: Model the sending and receipt as distinct communication activities in the sender’s process, ordered so that the sender waits for the result before giving feedback; represent repeated feedback and review as a loop until the stated acceptance condition is met.
