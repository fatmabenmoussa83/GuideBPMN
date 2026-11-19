# Learned guidelines: GPT-6 Luna, Reuse training, round 5 (44 descriptions)

103 generic and 2 example-specific error-driven guidelines; 41 generic guidelines confirmed. Full records (evidence, confirmation tests, provenance): `learned_guidelines.json`.

## Generic guidelines

**LRN-058** (T6; refines FID-03; 16 description(s); confirmed: yes)  
When the description states an activity or decision in terms of a specific action, object, or outcome: Label the corresponding BPMN element with concise wording that preserves that meaning; do not replace it with a broader stage name or add unsupported details.

**LRN-008** (T5; refines FID-01; 9 description(s); confirmed: yes)  
When the description says the process begins when a participant performs an action: Model the process trigger with a start event, then model the described action as an activity after that event; do not use the start event alone to represent the action.

**LRN-024** (T6; refines FID-03; 9 description(s); confirmed: yes)  
When the description states an activity together with a purpose, object, or scope that distinguishes what is being done: Label the corresponding BPMN task with its core action and enough of those stated details to preserve the activity’s meaning; do not add unsupported details or omit details that distinguish it.

**LRN-005** (T5; refines FID-02; 7 description(s); confirmed: yes)  
When the description states an order among process stages, describes branches that converge, or says that multiple required activities must finish before a later stage or process completion: Model the sequence flows that connect the corresponding elements, preserving the stated order and branch-and-join structure. Use gateway types that match whether the description specifies a choice or requires all branches to complete.

**LRN-036** (T5; refines GW-04; 6 description(s); confirmed: yes)  
When the description states that one activity continues while another activity occurs before a later step: Model the concurrent activities as parallel branches, then synchronize them before a later step that depends on both being complete.

**LRN-032** (T6; new; 5 description(s); confirmed: yes)  
When the description assigns an action to a particular participant or distinguishes that action from related actions: label each corresponding BPMN element with the described action and responsible participant; do not substitute another actor or conflate it with a separate action

**LRN-001** (T5; refines GW-04; 4 description(s); confirmed: yes)  
When the description presents multiple required activities within the same stage without specifying an order or a decision between them: model the activities as parallel branches from a parallel gateway

**LRN-006** (T5; refines ACT-07; 4 description(s); confirmed: yes)  
When the description states that an activity may take place before a shared continuation: Model an exclusive gateway that routes either through the optional activity or around it, then rejoin the paths before the shared continuation.

**LRN-011** (T6; refines FID-03; 4 description(s); confirmed: no)  
When the description states how the process begins or ends: Label the corresponding start and end events with the described trigger or outcome rather than generic labels.

**LRN-023** (T6; refines FID-03; 4 description(s); confirmed: yes)  
When the description gives an activity together with contextual or implementation details: label the corresponding BPMN element with its core action and object, omitting details that do not distinguish the activity.

**LRN-040** (T5; refines GW-01; 4 description(s); confirmed: yes)  
When the description states that a later action or outcome depends on the result of an assessment: Model the assessment as an activity followed by an exclusive gateway, with outgoing sequence flows for the described outcomes.

**LRN-087** (T5; refines GW-04; 4 description(s); confirmed: no)  
When the description states that two activities proceed concurrently, or that one activity occurs while another is underway: Model the concurrent work as separate branches from a parallel gateway, connecting the gateway to each branch’s activity with sequence flows. Join the branches only when subsequent work must await completion of both.

**LRN-030** (T3; refines PROC-03; 3 description(s); confirmed: no)  
When the description identifies an ongoing process phase that is followed by a stated activity or outcome: Model the phase so that its sequence flow continues to the subsequent activity or outcome, using a gateway if the described control flow requires a decision or synchronization.

**LRN-042** (T5; refines FLOW-01; 3 description(s); confirmed: yes)  
When the description states that one activity follows another in a specific order: Model the activities with sequence flows that preserve the stated order.

**LRN-056** (T6; refines FID-03; 3 description(s); confirmed: no)  
When the description distinguishes alternative paths by a condition that determines which outcome follows: Label the corresponding gateway with the decision condition being evaluated, rather than with a broad stage or outcome name.

**LRN-061** (T5; refines ACT-07; 3 description(s); confirmed: no)  
When the description states that an activity is followed by a decision or by work that must proceed in parallel: Connect the activity by sequence flow to the gateway that controls the stated outcomes or parallel branches.

**LRN-002** (T6; refines FID-01; 2 description(s); confirmed: yes)  
When the description states how the process ends or gives a conditional branch without stating that the branch terminates the process: Label an end event only with an outcome explicitly stated for process termination; do not assign it an inferred or unstated branch outcome.

**LRN-022** (T5; refines PROC-04; 2 description(s); confirmed: no)  
When the description identifies mutually exclusive outcomes for a process decision: Model an exclusive decision gateway with a separate outgoing path for each stated outcome, and ensure each path reaches its appropriate terminal outcome.

**LRN-025** (T5; refines PROC-04; 2 description(s); confirmed: no)  
When the description states that a process can end in two or more mutually exclusive outcomes: Model each outcome on its own branch from a decision gateway, connecting that branch to the corresponding outcome activity or end event.

**LRN-028** (T5; refines FID-01; 2 description(s); confirmed: no)  
When the description explicitly states a distinct assessment, review, or check as part of the process: Model that work as a separate BPMN activity and connect it according to the described dependencies; do not omit it or absorb it into another activity.

**LRN-047** (T5; refines FID-01; 2 description(s); confirmed: no)  
When the description states that a participant performs an initiating action before another participant begins the process work: Model the initiating action as an activity after a start event, rather than absorbing it into the start event.

**LRN-055** (T5; refines EVT-02; 2 description(s); confirmed: yes)  
When the description identifies a process path that finishes after its last described activity: Connect the last activity on each such path to an end event; use separate end events when the paths have distinct outcomes.

**LRN-071** (T5; refines FID-02; 2 description(s); confirmed: yes)  
When the description states that work proceeds through multiple dependent activities, including activities that must occur in parallel or overlap: Model their sequence flows and parallel branches to preserve the stated dependencies, synchronizing branches only when later work depends on their completion.

**LRN-073** (T6; new; 2 description(s); confirmed: yes)  
When the description says that an external item or resource arrives before subsequent work, without describing a separate receiving action: Model the arrival as an intermediate catch event that the process waits for, rather than inventing a receiving task; use a message catch event only when the description establishes that the arrival is communicated as a message.

**LRN-074** (T5; new; 2 description(s); confirmed: no)  
When the description presents alternatives for one part of a process while requiring other work to be completed before a later activity: Model the alternatives with an exclusive gateway and the required work as parallel branches; synchronize the required branches before the later activity that depends on their completion.

**LRN-079** (T5; refines ACT-07; 2 description(s); confirmed: yes)  
When the description establishes an order between activities or between an activity and a decision: Model the stated process steps and connect them with sequence flows in that order, including transitions to and from decision gateways.

**LRN-086** (T6; refines FID-03; 2 description(s); confirmed: yes)  
When the description states multiple distinct decision questions for different choices: Label each corresponding BPMN gateway with concise wording that faithfully identifies the question it evaluates; do not use wording from another decision.

**LRN-097** (T6; refines FID-02; 2 description(s); confirmed: yes)  
When the description identifies distinct activities, whether by their different purposes or effects or by their stated dependencies or order: Model each activity as a separate task and label it to preserve the action described; connect the tasks with sequence flows that preserve any stated dependencies and order.

**LRN-003** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that an activity follows another only after a condition or approval is met: Model the stated order with sequence flows, and use a decision gateway before the dependent activity to route the outcomes that the description specifies.

**LRN-004** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description explicitly identifies the recipient of an activity or output: Include that recipient in the corresponding task label when omitting it would make the task less specific or change its meaning.

**LRN-007** (T6; refines FID-03; 1 description(s); confirmed: yes)  
When the description says that a broader process stage begins and names activities included in it: Label the corresponding BPMN activity to express the start of that stage; do not label it as performing or finishing one of the included activities unless the description says so.

**LRN-009** (T6; refines FID-03; 1 description(s); confirmed: yes)  
When the description names components included in a broader process stage but does not specify the action performed for each component: label each corresponding activity neutrally with the stated component; do not imply that someone provides, performs, or completes it unless the description supports that action

**LRN-010** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description states that an observed value is assessed against a stated limit and that the result determines whether a subsequent response is needed: Model the assessment after the activity that observes the value as a decision gateway, with outgoing paths for the outcomes stated in the description, and route each response only along its applicable outcome.

**LRN-012** (T5; refines ACT-07; 1 description(s); confirmed: yes)  
When the description lists multiple required activities after the same event without specifying their order, and describes alternative ways to perform one of those activities: Model the required activities as parallel branches. Represent the alternatives with an exclusive gateway leading to a separate activity for each alternative.

**LRN-013** (T6; refines FID-02; 1 description(s); confirmed: no)  
When the description presents mutually exclusive destinations for placing or routing the same item: Model each destination-specific action as a separate BPMN task, with an exclusive gateway when only one destination is selected.

**LRN-014** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description presents alternative ways to detect or communicate that a condition requiring follow-up has occurred, including a human check: Model the stated alternatives on distinct paths, and model any described human check as an activity on its path.

**LRN-015** (T3; refines PROC-05; 1 description(s); confirmed: no)  
When the description indicates that optional work may be triggered by an event after the main flow has completed: Model the triggered work as a separate process, rather than as a detached start-to-end chain in the same process.

**LRN-016** (T3; refines FLOW-01; 1 description(s); confirmed: no)  
When the description states a process trigger followed by a subsequent activity: Connect the start event to the first activity with an outgoing sequence flow, preserving the stated execution order.

**LRN-017** (T5; new; 1 description(s); confirmed: no)  
When the description says that an ongoing activity continues until a stated condition occurs, and then states an outcome that follows: Model waiting for that condition with an intermediate catch event, then continue the flow to the stated outcome.

**LRN-018** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description identifies the object or information entity acted on by an activity: Label the corresponding BPMN activity using that stated entity rather than substituting a related but distinct one.

**LRN-019** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description states that the same process can be initiated through mutually exclusive channels: Model an exclusive gateway that branches to a separate activity for each channel.

**LRN-020** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description states that one participant sends an item or information to another participant: Label the corresponding BPMN activity from the sender’s perspective and preserve the sending action; do not replace it with the recipient’s receiving perspective.

**LRN-021** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a participant selects an option before continuing with later work: Model the selection as an explicit activity and place it in the sequence before the subsequent work.

**LRN-026** (T6; refines FID-04; 1 description(s); confirmed: no)  
When the description states an activity and lists multiple purposes or criteria for it: Label the corresponding task with the core activity and its stated object; do not narrow the label to just one of the listed purposes or criteria.

**LRN-027** (T6; refines FID-01; 1 description(s); confirmed: yes)  
When the description indicates that ongoing support is available after the main work is completed: Model the support as an activity in the process flow rather than mentioning it only in an end-event label.

**LRN-029** (T6; refines FID-04; 1 description(s); confirmed: no)  
When the description states a conditional branch but does not state the outcome when the condition is not met: Label any corresponding end event generically; do not infer an unstated outcome from the condition.

**LRN-031** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description indicates that an activity recurs at intervals during a longer-running process phase: Model the recurring activity as work within that phase and connect it to the surrounding process flow.

**LRN-033** (T3; refines GW-05; 1 description(s); confirmed: yes)  
When the description says that an activity continues while progress is evaluated and that a later outcome follows only when a stated condition is met: Model the condition as an intermediate catch event before the outcome, rather than using a parallel split or join that waits for a branch that may no longer be reachable.

**LRN-034** (T6; refines FID-03; 1 description(s); confirmed: yes)  
When the description states the business outcome that terminates the process: Label the corresponding end event with that stated outcome, rather than a different or contradictory outcome.

**LRN-035** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description presents stages as an ordered progression, with a later stage following completion of an earlier one: Model the stages with sequence flows that preserve the stated order; do not use a parallel split unless the description says the work proceeds concurrently

**LRN-037** (T5; refines ACT-05; 1 description(s); confirmed: yes)  
When the description says that a decision must be communicated to an affected participant: Model the communication as a distinct activity on each applicable outcome branch, separate from the decision itself and other branch-specific work.

**LRN-038** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that an internal handling activity occurs after a request and before a later response or decision: Model the handling activity as a separate activity in that order, rather than routing directly from the request to the response.

**LRN-039** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that reviews may recur and that feedback from those reviews can lead to changes: Model feedback and change work as explicit activities, and use a decision gateway with a loop to a review when another review may be needed.

**LRN-041** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that an approver may approve an item or return it for revision: Model approval as an explicit activity on the approval-outcome branch, before the next action that depends on approval.

**LRN-043** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a role or department performs a distinct operational activity as part of the process, including alongside other work: Model that activity as a separate BPMN task and connect it to the surrounding activities according to the described order or parallel structure.

**LRN-044** (T5; refines PROC-04; 1 description(s); confirmed: no)  
When the description states that a recurring process continues until one of multiple distinct outcomes occurs: Model a distinct exit path for each stated outcome and represent each outcome explicitly at termination, rather than collapsing them into an undifferentiated loop exit.

**LRN-045** (T6; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that a participant must choose among alternatives as part of the process: Model the choice explicitly as an activity in the flow, preserving its stated order and dependencies on other activities.

**LRN-046** (T5; refines SUB-05; 1 description(s); confirmed: no)  
When the description says that an activity occurs for every occurrence of an event or condition, and that another activity must follow each occurrence: Model the repeated activity and its required follow-up with a loop or return flow so that every occurrence leads to the follow-up activity.

**LRN-048** (T5; refines GW-06; 1 description(s); confirmed: yes)  
When the description lists multiple follow-up actions, with one required and another performed only when needed: Model the actions as branches from an inclusive gateway, activating the conditional branch only when applicable.

**LRN-049** (T7; refines LANE-02; 1 description(s); confirmed: no)  
When the description assigns an activity to a role and then describes a dependent continuation of that work without naming a different responsible role: Place the continuation in the same role’s lane unless the description assigns it to another role.

**LRN-050** (T7; refines FID-01; 1 description(s); confirmed: no)  
When the description states that an item is made ready for collection or handoff after other work is complete: Model the preparation as an activity in the responsible participant’s process.

**LRN-051** (T5; refines EVT-03; 1 description(s); confirmed: yes)  
When the description says an action follows when a deadline passes while an expected response or payment is still outstanding: Model the deadline with a timer intermediate catch event, using an event-based gateway when it competes with other possible events.

**LRN-052** (T7; refines COL-07; 1 description(s); confirmed: yes)  
When the description mentions an external party only as the recipient of a communication or as the source of a response or event, without describing that party’s own actions in the process: do not create a separate participant pool or message flows solely from that mention; add them only when the description establishes the party’s participation in the collaboration

**LRN-053** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description states mutually exclusive conditions that lead to different terminal outcomes: Model the alternatives as separate branches from an exclusive decision gateway, with each branch leading to its corresponding terminal outcome.

**LRN-054** (T7; refines COL-01; 1 description(s); confirmed: no)  
When the description is narrated in the first person and the narrator performs process activities: Represent the narrator as a participant pool in the collaboration.

**LRN-057** (T7; refines COL-07; 1 description(s); confirmed: no)  
When the description identifies a software system separate from the process’s own system and describes process interaction through it, such as initiating the process or receiving its results: Model that system as a separate participant pool, not as a lane in the process, and use message flows for the interactions between the pools.

**LRN-059** (T5; refines ACT-05; 1 description(s); confirmed: no)  
When the description says a process may send an initial status notification, continue processing, and communicate the outcome asynchronously afterward: Model the notification and continued processing as distinct steps, and represent receipt of the asynchronous communication with a message-catching event connected to the outcome path.

**LRN-060** (T7; refines ACT-05; 1 description(s); confirmed: yes)  
When the description says an external participant sends information to an internal process, which then makes that information available through a user-facing interface: Model the incoming communication to a message-catching event in the internal process, and model making the information available through the interface as a separate internal activity; do not direct the external message to the interface.

**LRN-062** (T5; refines ACT-04; 1 description(s); confirmed: no)  
When the description assigns a participant a recurring obligation to provide information but does not describe a separate recipient-side receipt or explicitly state that the communication is modeled as a message exchange: Model the obligation as work performed by that participant; do not invent separate send and receive tasks.

**LRN-063** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description places a decision at the end of a defined activity or period: Connect completion of that activity or period to the decision with a sequence flow. When the decision determines mutually exclusive outcomes, use an exclusive gateway and connect each outcome to its corresponding path.

**LRN-064** (T3; refines GW-06; 1 description(s); confirmed: yes)  
When the description states that multiple follow-up obligations apply independently, with applicability varying by circumstance: Model the obligations as independently activated conditional branches; if they converge, use an inclusive join so that only activated branches are awaited.

**LRN-065** (T5; refines PROC-04; 1 description(s); confirmed: no)  
When the description lists multiple kinds of occurrences that require the same initial notification: Model one shared start event and the common notification, then use a gateway to branch by occurrence type rather than creating a separate start event for each type.

**LRN-066** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description makes subsequent actions depend on a stated event category or seriousness, prior notification, or an eligibility or status criterion: Model each stated distinction with a decision gateway and condition-labeled sequence flows to the applicable follow-up actions; do not represent a conditional continuation as an independent process start event.

**LRN-067** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description specifies items that must be submitted or presented as part of an application: model an activity to collect and organize those items before the application is submitted

**LRN-068** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says that required inputs may differ among cases or that more inputs may be requested: Model a decision about whether additional inputs are needed and an optional path for obtaining them before continuing.

**LRN-069** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description explicitly states that reaching agreement with another party is required as part of obtaining or arranging a resource or service: Model the agreement-making work as a distinct activity in the process flow, connected according to the described dependencies; do not omit it or represent only related information-gathering or administrative work.

**LRN-070** (T5; refines EVT-03; 1 description(s); confirmed: no)  
When the description makes a decision depend on responses from other participants and indicates that those responses must be received before the decision can be evaluated: Model an intermediate catch event for waiting for the responses before evaluating the decision.

**LRN-072** (T6; new; 1 description(s); confirmed: no)  
When the description says that work proceeds after items arrive, without stating a separate action to receive them: Model the arrival as an intermediate catch event when it is a prerequisite for subsequent work; do not add a separate receiving activity unless the description explicitly describes one.

**LRN-075** (T5; refines GW-04; 1 description(s); confirmed: no)  
When the description says that one communication is sent to multiple recipients and that each recipient should receive it: Model delivery to each recipient separately, using parallel branches when delivery to all recipients is required.

**LRN-076** (T5; refines SUB-05; 1 description(s); confirmed: yes)  
When the description states that an exchanged output is subject to further changes based on additional input: Model sending the input and receiving the updated output as a repeating feedback cycle, with an explicit decision whether to repeat the cycle or continue.

**LRN-077** (T7; refines COL-01; 1 description(s); confirmed: no)  
When the description states that a process participant sends a request or information to an external party and describes that party returning information or otherwise responding: Model the external party as a separate participant pool, keep the sending and receiving work or events in the process participant’s own pool, and represent the exchanges with message flows.

**LRN-078** (T5; refines FID-02; 1 description(s); confirmed: yes)  
When the description states that an activity initiates processing and that processing continues while other work takes place: Model the initiating activity as a task and the completion of processing as an intermediate catch event; do not model the wait itself as a task.

**LRN-080** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says a participant provides multiple distinct inputs that determine later system-provided outputs: Model a separate activity for each input before the system produces those outputs.

**LRN-081** (T6; new; 1 description(s); confirmed: no)  
When the description says that a digital system supplies information to a user: model the system's act of presenting that information as an activity, rather than modeling the user's receipt of it or an unstated preparatory action.

**LRN-082** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says that a procedure is carried out after receiving directions and later distinguishes outcomes by whether it succeeds: Model the procedure as a distinct activity after the directions are received and before the outcome decision, preserving that order with sequence flows.

**LRN-083** (T5; new; 1 description(s); confirmed: no)  
When the description says that multiple distinct pieces of information are collected and are all needed for a later calculation: Model the information-collection work as parallel branches and synchronize those branches before the calculation that depends on all of them.

**LRN-084** (T5; refines EVT-03; 1 description(s); confirmed: no)  
When the description says ongoing work should resume when an external trigger occurs: Model the wait for that trigger with an intermediate catch event, and connect it to the activity that resumes the work.

**LRN-085** (T5; refines PROC-03; 1 description(s); confirmed: no)  
When the description says a participant may optionally perform a final activity: Model the activity on an optional path, with a path that skips it, and connect its completion to an end event.

**LRN-088** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that activities occur in a particular order or overlap, including around a choice or concurrent work: Model sequence flows and gateways to preserve those dependencies and transitions.

**LRN-089** (T5; refines PROC-04; 1 description(s); confirmed: no)  
When the description identifies a participant action as the process beginning and describes a conditional outcome that ends the process before the normal path completes: Model an explicit start event before the action, and route the early-ending and normal-completion outcomes to appropriate end events.

**LRN-090** (T6; refines FID-01; 1 description(s); confirmed: yes)  
When the description explicitly says that a condition, status, or readiness is checked before outcomes are selected: Model the check as an activity before the gateway that routes according to its result.

**LRN-091** (T5; refines GW-02; 1 description(s); confirmed: yes)  
When the description says that items are processed in turn, an overall completion condition is checked, and another item is selected for processing if the condition is not met: Model the completion check as an exclusive split: route the unmet-condition path through next-item selection and back to item processing, and route the met-condition path onward. Converge the initial entry and repeat path at the item-processing entry with an exclusive merge gateway.

**LRN-092** (T6; new; 1 description(s); confirmed: no)  
When the description gives a process title but no separate initiating condition and then describes the first activity: Label the start event with the process title rather than a generic label.

**LRN-093** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that an activity is followed by another activity or by a control-flow gateway: Model the transition with a sequence flow so the control flow preserves the stated order.

**LRN-094** (T1; refines XML-06; 1 description(s); confirmed: no)  
When the description specifies conditions that determine which sequence-flow branch is taken: Serialize each corresponding BPMN conditionExpression using only attributes permitted by the BPMN 2.0.2 schema; do not include a language attribute.

**LRN-095** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that a distinct measurement is associated with an activity and that a later decision depends on the measured value: Model the measurement as a separate activity, and ensure the decision occurs only after the activity and measurement are complete.

**LRN-096** (T6; refines FID-02; 1 description(s); confirmed: no)  
When the description presents multiple coordinated actions as one activity: Model the stated activity as one BPMN task and label it to preserve all of its coordinated actions; do not split the actions into separate tasks unless the description gives a process reason to do so.

**LRN-098** (T5; refines FLOW-07; 1 description(s); confirmed: no)  
When the description says that an unfavorable decision sends work back and identifies an earlier activity to resume: Model a decision branch with a return sequence flow to that activity, so the described loop is explicit.

**LRN-099** (T6; new; 1 description(s); confirmed: no)  
When the description distinguishes a completed state or milestone from a subsequent activity performed on the same object: Label the task for the subsequent activity with the described action, rather than with the preceding state or milestone.

**LRN-100** (T6; new; 1 description(s); confirmed: yes)  
When the description identifies an activity’s responsible or addressed role more specifically than a department or generic role: Preserve that role specificity in the corresponding BPMN element’s label rather than generalizing it to the broader department or role.

**LRN-101** (T5; refines COL-03; 1 description(s); confirmed: yes)  
When the description says that one participant sends an item to another participant and describes the recipient acting on it: Model the participants’ work in their respective processes and connect the communication with a message flow between their pools; keep sequence flows within each participant’s process.

**LRN-102** (T6; new; 1 description(s); confirmed: yes)  
When the description states that a decision can lead to two or more mutually exclusive actions: Model each alternative on its own exclusive branch, and represent each stated action with its own activity; use a terminal outcome instead when the description states only an outcome.

**LRN-103** (T5; refines FLOW-06; 1 description(s); confirmed: yes)  
When the description says that one or more failure branches return to an earlier activity that is also reached by the initial forward path: Model an exclusive gateway before that activity to merge the initial forward path and the alternative return paths.

## Example-specific guidelines

**EXS-014** (T5; refines FLOW-07; 1 description(s); confirmed: no)  
When the description states that a process repeats until one of several terminal outcomes occurs: Model a decision that routes each terminal outcome out of the cycle and routes the continuing outcome back into the cycle.

**EXS-022** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that distinct activities depend on one another or must occur in a specified order: Model each activity separately and connect the activities with sequence flows that preserve the stated dependencies and order.
