# Learned guidelines: GPT-6 Luna, Reuse training, round 2 (44 descriptions)

87 generic and 3 example-specific error-driven guidelines; 37 generic guidelines confirmed. Full records (evidence, confirmation tests, provenance): `learned_guidelines.json`.

## Generic guidelines

**LRN-016** (T6; refines FID-03; 26 description(s); confirmed: yes)  
When the description states an activity or outcome and identifies its action, object, actor, or recipient: label the corresponding BPMN element with concise wording that preserves those stated details and does not substitute a different action or meaning

**LRN-003** (T6; refines FID-01; 14 description(s); confirmed: yes)  
When the description names a distinct activity or outcome and states its action or completion condition: Label the corresponding BPMN element with the described action or outcome. Do not replace it with a broader or narrower action, or add detail the description does not support.

**LRN-001** (T5; refines ACT-07; 10 description(s); confirmed: yes)  
When the description lays out activities in an order, or requires several activities to finish before a later stage or process end: Connect the activities with sequence flows that preserve the stated order; when every required activity must finish before proceeding, synchronize their paths with a parallel gateway.

**LRN-034** (T5; refines GW-04; 7 description(s); confirmed: yes)  
When the description states that two or more actions occur at the same time, or that one action is independent of another after a shared prerequisite: Model the actions on separate branches from a parallel gateway. Use a parallel join only before a continuation that requires all those branches to finish.

**LRN-011** (T5; refines FID-01; 5 description(s); confirmed: yes)  
When the description says that an actor performs an action that initiates the process: Model the process trigger with an appropriate start event, then model the described action as an activity after that event; do not use the start event as a substitute for the action.

**LRN-052** (T5; refines FLOW-01; 5 description(s); confirmed: yes)  
When the description specifies successive activities or a transition into or out of a decision or synchronization point: Connect the corresponding flow nodes with sequence flows so the modeled paths preserve the described order and branch continuation.

**LRN-037** (T5; refines GW-07; 4 description(s); confirmed: yes)  
When the description specifies what activity or process end follows an activity, a decision outcome, or a catching event, or describes waiting for alternative events: Model each described transition with a sequence flow to its stated next activity or process end. For an event-based gateway, connect each branch first to the corresponding catching event, then continue that path to its described follow-up.

**LRN-040** (T5; refines FLOW-01; 4 description(s); confirmed: no)  
When the description states that an activity, event, or decision outcome leads to a specific next action: connect the corresponding BPMN elements with sequence flows, including the stated successor of each branch

**LRN-005** (T5; refines GW-01; 3 description(s); confirmed: yes)  
When the description presents mutually exclusive alternatives for where or how an item is handled: Model the choice with an exclusive gateway and separate alternative paths, then merge them before any shared next step.

**LRN-009** (T6; refines FID-03; 3 description(s); confirmed: yes)  
When the description gives an activity with multiple evaluation dimensions or optional methods, or states a completion outcome in detail: Use concise labels for the corresponding BPMN activities and events, preserving the central action or outcome without enumerating subsidiary details.

**LRN-014** (T6; refines FID-03; 3 description(s); confirmed: yes)  
When the description explicitly names multiple operations or specifies an activity’s object or recipient: Retain those stated details in the corresponding BPMN activity label so the label does not broaden or narrow the described work.

**LRN-015** (T5; refines FID-01; 3 description(s); confirmed: no)  
When the description states that a participant enters information or other inputs as a distinct action: Model that action as a separate activity in the appropriate sequence; do not omit it or absorb it into another activity.

**LRN-021** (T6; refines FID-04; 3 description(s); confirmed: no)  
When the description specifies what happens when a condition is met but does not state the outcome when it is not met: Do not infer a specific outcome for the alternative path; use a generic end-event label unless the description states that outcome.

**LRN-029** (T5; refines ACT-07; 3 description(s); confirmed: yes)  
When the description names multiple required activities that must be completed before a later activity, without specifying an order among them: Model the activities as separate parallel branches and synchronize them before the later activity.

**LRN-049** (T3; refines ACT-07; 3 description(s); confirmed: no)  
When the description makes an action conditional on whether a stated condition holds: Model the condition as a control-flow decision with alternative outgoing paths, so the action is taken only on the applicable path; do not use a gateway with only one incoming and one outgoing sequence flow.

**LRN-069** (T6; new; 3 description(s); confirmed: yes)  
When the description states who performs an activity, who receives a communication, or what outcome or condition occurs: Label each BPMN element to preserve the described action, actor or recipient, and outcome; do not change who sends or receives a communication or replace a stated activity or outcome with a different one.

**LRN-004** (T5; refines ACT-07; 2 description(s); confirmed: yes)  
When the description says an activity may or may not occur before the process continues: Model mutually exclusive paths for performing or skipping the activity, then merge the paths before the next step.

**LRN-006** (T5; refines ACT-07; 2 description(s); confirmed: yes)  
When the description says that distinct activities happen independently during the same ongoing period: Model the activities as separate branches from a parallel gateway rather than sequencing them, and synchronize the branches only if all must finish before the process continues.

**LRN-017** (T5; refines FLOW-01; 2 description(s); confirmed: yes)  
When the description places a decision or synchronization point after an activity: Connect the preceding activity to that gateway with a sequence flow in the same process scope; do not omit the transition.

**LRN-032** (T5; new; 2 description(s); confirmed: no)  
When the description states a decision with multiple distinct outcomes: Model the decision as a gateway and connect it by a sequence flow to every described outcome branch.

**LRN-042** (T7; refines COL-04; 2 description(s); confirmed: no)  
When the description describes distinct participants communicating or exchanging an item, with an action by each participant: Model each described exchange as a message flow from the sending interaction node to the receiving interaction node in separate participant pools; represent distinct exchanges separately rather than combining them into one interaction.

**LRN-046** (T5; refines ACT-08; 2 description(s); confirmed: no)  
When the description explicitly states that a person or participant must perform an activity: Model that activity as a user task rather than a generic task.

**LRN-055** (T5; refines FID-02; 2 description(s); confirmed: no)  
When the description says an activity can begin only after a preceding activity or prerequisite stage is complete, including when it acts on that activity’s output: Model the activity as a separate task connected from the preceding flow by a sequence flow, not as a start event.

**LRN-056** (T5; refines ACT-04; 2 description(s); confirmed: yes)  
When the description says to send a request or provide input to another participant and then make later work depend on receiving that participant’s response: Model the response as a receiving activity or message-catching event, as appropriate, and connect the sending activity to it with a sequence flow before the dependent work.

**LRN-072** (T6; refines FID-03; 2 description(s); confirmed: yes)  
When the description states a choice between alternatives that determines which branch is taken: Label the corresponding BPMN gateway to express that choice, and label its outgoing branches with the stated alternatives; do not substitute a different decision or an unsupported condition.

**LRN-074** (T5; refines ACT-07; 2 description(s); confirmed: yes)  
When the description says that an actor checks whether a condition holds before the process branches: Model the check as a separate activity before the gateway, and use the gateway to represent the resulting alternatives.

**LRN-078** (T5; refines ACT-07; 2 description(s); confirmed: no)  
When the description identifies alternative outcomes or case types that require different follow-up paths, with one path possibly returning to earlier work: Model an exclusive gateway with a separate flow to each applicable follow-up path, including a return flow when a path resumes earlier work.

**LRN-002** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description states the purpose or destination of an activity: Include that stated purpose or destination in the BPMN activity label, rather than labeling only the broader action.

**LRN-007** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description gives an overall process context that also applies to individual activities, while the activities themselves are stated without repeating that context: Use concise task labels that preserve each described action and its scope; do not repeat the overall process context in a task label unless it distinguishes that activity from other activities.

**LRN-008** (T5; new; 1 description(s); confirmed: no)  
When the description says an activity continues during a defined period and that a later evaluation occurs after that period ends: Model the period end as a catching time event. If the evaluation must wait for both the period to end and the ongoing activity to finish, synchronize those paths with a parallel gateway before the evaluation.

**LRN-010** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description states an activity and a later, distinct outcome: Label each BPMN element with only the action or outcome it represents; do not combine them in one activity label.

**LRN-012** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says work proceeds until a condition is met and specifies the result of meeting it: Model the stated result explicitly on the path where the condition is satisfied, before the process ends.

**LRN-013** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description states that the same process can be initiated through mutually exclusive alternative channels or methods: Model the alternatives with an exclusive gateway after the start event, with each outcome representing one alternative.

**LRN-018** (T6; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that one outcome may be achieved through several distinct methods: Model the stated methods as explicit alternatives rather than subsuming them in one generic activity.

**LRN-019** (T5; refines FID-02; 1 description(s); confirmed: yes)  
When the description states that a participant submits information and that it is subsequently entered into a record or system: Model submission and recording as distinct activities connected in the stated order.

**LRN-020** (T6; refines FID-02; 1 description(s); confirmed: no)  
When the description identifies multiple distinct assessment criteria or activities within a broader assessment: Model each distinct assessment criterion or activity as a separate BPMN task rather than combining them into one broad task.

**LRN-022** (T3; refines GW-04; 1 description(s); confirmed: no)  
When the description says that an ongoing activity or review continues until a milestone is reached, and that later progression depends on reaching it: Model a conditional decision at the milestone check: route the not-yet-reached outcome back to the ongoing activity or review, and the reached outcome onward. Do not use a parallel split for these mutually exclusive outcomes.

**LRN-023** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says that meeting a milestone or prerequisite leads a person or case to be assessed for a possible next step: Model the assessment as an activity on the path where the milestone or prerequisite is met, before modeling the resulting decision or action.

**LRN-024** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says a review determines whether a stated outcome may proceed: Model the review as an activity and the approval as a decision; connect the approved branch to the stated outcome without adding a separate approval activity unless the description states one.

**LRN-025** (T5; refines ACT-08; 1 description(s); confirmed: no)  
When the description states an action performed within the process but does not state that the action sends a message to another participant: model the action as a regular task, not a send task

**LRN-026** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description says to communicate a decision but does not limit that communication to a positive or negative outcome: Use a neutral activity label that covers communicating either outcome; do not imply approval or rejection.

**LRN-027** (T5; refines FLOW-07; 1 description(s); confirmed: no)  
When the description says work may be evaluated and changed repeatedly in response to evaluation feedback: Model a decision-controlled cycle that routes work needing further changes back for another evaluation and lets work needing no further changes proceed. Model providing feedback as a separate activity when the description states that it is performed work.

**LRN-028** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that a review or assessment is performed and separately describes identifying its findings: model the review or assessment as an activity before modeling the identification of those findings

**LRN-030** (T3; refines PROC-05; 1 description(s); confirmed: yes)  
When the description says follow-on work starts only if a later event or condition occurs after the main flow: Model the follow-on work as a conditional continuation, an event subprocess, or a separate process whose start event represents that trigger; do not leave it as an unrelated detached start-to-end chain.

**LRN-031** (T5; refines EVT-03; 1 description(s); confirmed: yes)  
When the description says that a participant performs an action to confirm or verify that an outcome occurred: Model the confirmation as an activity; use a catch event only when the description says the process waits for a message, signal, time, or condition.

**LRN-033** (T5; refines FLOW-07; 1 description(s); confirmed: no)  
When the description says that an activity may recur and that each occurrence requires a subsequent activity to happen again: Model the recurring behavior with a gateway-controlled path that ensures each occurrence is followed by the required subsequent activity, rather than using only a one-time direct sequence.

**LRN-035** (T6; refines GW-06; 1 description(s); confirmed: no)  
When the description states that one action must occur while another action occurs only if a condition holds: Model the actions as branches from an inclusive gateway, with the mandatory branch always activated and the conditional branch activated when its condition holds; use an inclusive join to synchronize the activated branches before continuing.

**LRN-036** (T7; new; 1 description(s); confirmed: yes)  
When the description mentions an in-scope role contacting external providers and choosing among their responses, but does not describe the providers’ work beyond making those responses: Model the described contact and selection within the in-scope process; do not add an external pool or message flows solely to represent the implied request and responses.

**LRN-038** (T6; new; 1 description(s); confirmed: yes)  
When the description presents a decision whose outcome depends on a stated condition: Label the gateway with a concise question that names the stated condition, rather than a vague confirmation prompt.

**LRN-039** (T7; refines COL-07; 1 description(s); confirmed: yes)  
When the description mentions sending information to, or receiving a response, payment, or other input from, an external party but describes no process work performed by that party: Model the described work and any necessary communication or waiting within the in-scope process; do not add a separate participant pool or message flows solely because the external party is mentioned.

**LRN-041** (T7; refines COL-01; 1 description(s); confirmed: yes)  
When the description narrates work in the first person but does not explicitly name the narrator’s role: Represent the narrator who performs that work as a participant pool in the BPMN collaboration, with the narrated activities in that participant’s process.

**LRN-043** (T5; refines EVT-03; 1 description(s); confirmed: no)  
When the description says that a participant is given a physical item or device for use before a later notification: Model receiving the item as an activity, and model waiting for the later notification as an intermediate catch event before the described follow-up activity.

**LRN-044** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description states an activity or event together with contextual details that do not change its core action or outcome: Use a concise label for the core action or outcome, adding contextual details only when needed to distinguish its meaning from other modeled elements.

**LRN-045** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description explicitly states that a participant transfers or receives value as a distinct step in a workflow: model that action as an activity in the stated sequence

**LRN-047** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description says that a participant carries out an activity over a period before making a later decision: Model the activity before the decision; do not use an event marking the period's end as a substitute for the activity.

**LRN-048** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says that information is to be obtained from an external organization after that organization has been notified: Model a distinct follow-up activity to receive or obtain that information after the notification.

**LRN-050** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description assigns separate reports to different recipients or states that one report is required regardless of whether another report occurred: model each required report on its own control-flow path, retaining its stated applicability and timing

**LRN-051** (T5; refines EVT-03; 1 description(s); confirmed: no)  
When the description says that a decision or subsequent activity depends on participants replying with information or confirming availability: Model the wait for those replies as an intermediate catch event before the dependent flow continues.

**LRN-053** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description says that after a process or activity is complete, several optional follow-up actions may be chosen, including combinations of those actions: Model the choice with an inclusive gateway and a separate outgoing branch for each optional action, allowing any nonempty combination to be taken.

**LRN-054** (T7; refines LANE-01; 1 description(s); confirmed: no)  
When the description identifies both a human user and an automated system as distinct actors with different responsibilities: Represent their stated work in separate lanes within the process, unless the description establishes them as independently communicating participants, in which case represent them as separate pools.

**LRN-057** (T5; new; 1 description(s); confirmed: yes)  
When the description says to send work to another participant and request changes until an acceptance condition is met, without describing distinct incoming messages for each iteration: Model one response-receiving activity or message-catching event before the acceptance decision, and loop the exchange through that decision; do not add separate receiving elements for inferred intermediate responses.

**LRN-058** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says several items are processed separately, each must pass a check, unsuccessful items are revised and processed again, and a later activity may proceed only after every item passes: Model the per-item repetition and success decision, loop unsuccessful items through the stated rework, and synchronize successful items before the later activity.

**LRN-059** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description says that work begins when a specified event occurs: Model the specified event as a trigger in the continuing flow and the described work as an activity after it, not as an end event.

**LRN-060** (T6; refines ACT-05; 1 description(s); confirmed: no)  
When the description states that a participant requests or orders goods and separately states that the goods are delivered or received: Model the request or order and the receipt as distinct flow elements; represent receipt as a receiving activity or an appropriate catching event, not as another activity that sends an order.

**LRN-061** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a participant orders goods or materials from an external provider: Model placing the order as a distinct activity in the process.

**LRN-062** (T5; refines EVT-03; 1 description(s); confirmed: yes)  
When the description says an order is placed and separately says that processing must finish before the flow continues: Model placing the order as an activity, then model waiting for processing to finish as an intermediate catch event, not as a receive task.

**LRN-063** (T7; refines COL-01; 1 description(s); confirmed: yes)  
When the description says that the process sends information to an external participant and later receives a response from that participant: Model the external participant as a separate pool, connect the outgoing communication to that participant with a message flow, and represent the incoming response with a message catch event in the process, connected to the participant by a message flow.

**LRN-064** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a system performs or provides multiple distinct functions or outputs: Model each stated function or provision as a separate activity, rather than combining them into one generic activity or omitting them.

**LRN-065** (T5; refines ACT-02; 1 description(s); confirmed: yes)  
When the description says a person is told how to perform a procedure and later indicates whether it succeeded: model the person performing that procedure as a manual task after the guidance and before the outcome is assessed

**LRN-066** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description explicitly states that an automated system performs one or more actions during a process, alongside any human actions: Model each stated automated action as a separate activity from any human action, and connect the activities according to the dependencies stated in the description.

**LRN-067** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description says whether follow-up work occurs depends on an evaluation, but does not state the decision criterion: Label the decision gateway only with the stated dependency; do not name an unstated criterion or outcome.

**LRN-068** (T5; refines EVT-03; 1 description(s); confirmed: no)  
When the description says that a participant will arrive at an unpredictable time before work can proceed: model waiting for that arrival as an intermediate catch event, followed by the work performed upon arrival.

**LRN-070** (T6; refines EVT-03; 1 description(s); confirmed: no)  
When the description says that a participant receives message updates while waiting for another activity to finish: Model the wait for those updates as an intermediate message catch event, not as an activity that sends them.

**LRN-071** (T5; refines GW-01; 1 description(s); confirmed: yes)  
When the description states that one participant presents alternatives to another participant, whose selection determines which subsequent work is performed: Model obtaining the selection as an interaction activity (a user task when a person must respond), followed by an exclusive gateway that routes the alternatives; do not model the interaction as separate send and receive tasks.

**LRN-073** (T5; refines EVT-03; 1 description(s); confirmed: no)  
When the description says that updates are provided at regular time intervals while other work is still in progress: Model each update as a distinct action followed by an intermediate timer catch event, and repeat the update-and-wait cycle until the ongoing work is complete.

**LRN-075** (T5; refines GW-04; 1 description(s); confirmed: yes)  
When the description says a repeated set of activities continues until a completion condition is met, after which multiple activities begin simultaneously: Connect the loop’s completion path to a parallel gateway that starts the concurrent branches.

**LRN-076** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description provides a process title but does not state a distinct start trigger: Do not use the process title as the start-event label; use a concise label only when the description supports a meaningful trigger.

**LRN-077** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description states an activity, condition, or outcome that is represented by a BPMN element: Label the element and, where applicable, its outgoing branches so they preserve the meaning stated in the description; do not change, swap, or add semantic details.

**LRN-079** (T6; new; 1 description(s); confirmed: no)  
When the description states that a participant checks an item and explicitly assigns or records its status before the process branches: Model the check and status assignment as distinct activities before a gateway; use the gateway to route the flow according to the assigned status.

**LRN-080** (T6; refines FID-02; 1 description(s); confirmed: no)  
When the description states distinct actions performed in sequence by one or more participants: Model each stated action as a separate activity, using a label that preserves that action and its object; do not use a neighboring activity or a decision gateway to stand in for it.

**LRN-081** (T6; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that a person checks an item and then marks it or assigns it a status: Model the checking and marking as separate activities, followed by a gateway that routes the process according to the stated status; do not use the gateway in place of either activity.

**LRN-082** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description presents mutually exclusive alternative actions or outcomes: Model an exclusive gateway before the alternative actions, with a separate outgoing branch for each alternative; do not model the alternatives as actions that all occur.

**LRN-083** (T5; refines GW-01; 1 description(s); confirmed: no)  
When the description presents mutually exclusive alternative actions, each with a distinct stated outcome: Model an exclusive gateway before the alternative actions, with each branch leading to its corresponding action and outcome.

**LRN-084** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that one participant sends information or an item to another participant before the recipient performs a subsequent activity: model the sending action as an activity in the sender’s process, represent the communication with a message flow to the recipient’s process, and preserve the stated order within each participant’s process without using sequence flows across pools

**LRN-085** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that an actor checks or examines something and then performs a distinct response based on the outcome: Model the check and the response as separate activities, with the response following the check.

**LRN-086** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says that an actor checks or examines something and then performs a distinct response depending on the result: Model the check and response as separate activities, with the response following the check; represent any stated outcome-dependent alternatives in the flow using an appropriate decision gateway.

**LRN-087** (T5; refines GW-01; 1 description(s); confirmed: yes)  
When the description says that a failed check returns the process to an earlier activity that is also reached on the initial route: Model a converging exclusive gateway before the repeated activity, and route both the initial path and each retry path through it.

## Example-specific guidelines

**EXS-006** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description explicitly states that a distinct activity is performed on the output or items of an earlier activity: Model the stated activity as a separate BPMN activity and preserve the described order with sequence flows.

**EXS-009** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description says that actions happen simultaneously and that a later action follows one of them while remaining independent of the activities on another concurrent branch: Model the concurrent actions on separate parallel branches. Put the later action on the branch it follows, and do not make it wait for an unrelated branch to finish. Synchronize branches only when the description requires them to reunite.

**EXS-013** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description states that a shared notification can concern different kinds of occurrences and that the follow-up handling depends on the occurrence kind or its attributes: Model an exclusive gateway after the shared notification to route each case to its applicable follow-up path.
