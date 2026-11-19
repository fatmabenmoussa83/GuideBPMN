# Learned guidelines: GPT-6 Luna, Revised, run 1

97 generic and 3 example-specific error-driven guidelines; 38 generic guidelines confirmed. Full records (evidence, confirmation tests, provenance): `learned_guidelines.json`.

## Generic guidelines

**LRN-020** (T6; refines FID-03; 29 description(s); confirmed: yes)  
When the description distinguishes an event or activity by its action, actor, object, recipient, or another meaningful qualifier: Label each BPMN element so that it preserves those stated details without substituting a broader or different meaning.

**LRN-010** (T5; refines ACT-07; 19 description(s); confirmed: yes)  
When the description states that several activities are all required before a later activity or outcome: Model the activities as parallel branches and synchronize all branches with a parallel gateway before the later activity or outcome.

**LRN-026** (T5; refines PROC-03; 16 description(s); confirmed: yes)  
When the description states a sequence of activities or a conditional step followed by a later activity: Connect the activities and any modeled gateways in the stated order with sequence flows, including every described transition.

**LRN-062** (T6; refines FID-03; 14 description(s); confirmed: yes)  
When the description states a specific action, decision, or outcome, but a generated BPMN element label expresses a different meaning: Label the element to preserve the meaning of the corresponding described step; do not substitute another action, decision, outcome, or an inferred purpose.

**LRN-007** (T6; refines FID-03; 11 description(s); confirmed: yes)  
When the description distinguishes a process trigger, an activity, or an outcome from other stages of the process: Label each BPMN element according to the meaning of its corresponding described trigger, activity, or outcome; do not substitute a different stage or its purpose or result.

**LRN-008** (T5; refines EVT-01; 7 description(s); confirmed: yes)  
When the description says that a participant performs an action that initiates the process: Model the process trigger with a start event, then model the participant’s described action as a distinct task; do not use the action itself as the start event.

**LRN-003** (T6; refines FID-03; 6 description(s); confirmed: yes)  
When the description specifies an activity’s object, recipient, or other meaningful qualifier: Preserve that qualifier in the BPMN task label rather than replacing it with a broader paraphrase.

**LRN-005** (T6; refines EVT-01; 6 description(s); confirmed: yes)  
When the description states an occurrence that starts the process: Label the start event with a concise phrase naming that trigger rather than a generic label.

**LRN-009** (T5; refines GW-03; 5 description(s); confirmed: yes)  
When the description says an activity may or may not occur before a later required activity: model the optional activity as one branch of an exclusive gateway, and merge the branches before the later required activity

**LRN-012** (T6; refines FID-03; 3 description(s); confirmed: yes)  
When the description explicitly states the outcome that marks the process as complete: label the end event with a concise phrase that faithfully names that outcome, rather than a generic label or an unnecessarily detailed restatement

**LRN-017** (T6; refines FID-02; 3 description(s); confirmed: yes)  
When the description presents two or more distinct activities as alternatives: Model each activity as a separate task on its own branch rather than combining the alternatives into one task; choose a gateway that matches whether one or multiple alternatives may be performed.

**LRN-036** (T5; refines FID-01; 3 description(s); confirmed: yes)  
When the description states that a condition or decision leads to a distinct action before subsequent work: Model the action as a separate task on the corresponding branch, and connect it to the preceding and subsequent work as described, including any return flow.

**LRN-046** (T7; refines FID-01; 3 description(s); confirmed: no)  
When the description states that an internal process sends information or an item to an external participant, or receives information or an item from one: Model the external participant as a separate pool and represent the stated communications with message flows.

**LRN-081** (T6; refines ACT-05; 3 description(s); confirmed: no)  
When the description assigns an action to a participant or states the direction of an interaction: Preserve who performs or receives the action and its direction in the BPMN element label; do not relabel receipt as sending or otherwise change the stated action.

**LRN-002** (T6; refines FID-03; 2 description(s); confirmed: yes)  
When the description identifies a condition for taking a branch but does not say that the alternative ends the process: Label an end event only with an outcome explicitly stated as the process outcome; otherwise use a neutral end-event label.

**LRN-006** (T5; refines FID-02; 2 description(s); confirmed: no)  
When the description states that a subsequent phase starts only after a stated condition is met: Connect that phase to the branch representing the condition being met, rather than leaving it disconnected.

**LRN-013** (T5; refines ACT-07; 2 description(s); confirmed: yes)  
When the description presents mutually alternative ways to signal the same need and identifies a shared subsequent activity: Model the alternatives as exclusive branches and merge them before the shared activity.

**LRN-019** (T5; refines FID-02; 2 description(s); confirmed: yes)  
When the description explicitly orders activities or says that work continues until a stated condition is reached: Model the activities in the stated sequence, and do not represent them as parallel or mutually exclusive branches unless the description explicitly supports concurrency or a decision.

**LRN-025** (T6; refines FID-03; 2 description(s); confirmed: yes)  
When the description gives an activity together with contextual or explanatory details that are not needed to distinguish the activity in its process context: Label the BPMN task with its core action and necessary object, omitting redundant contextual modifiers while preserving details essential to the activity’s meaning.

**LRN-034** (T5; refines FID-01; 2 description(s); confirmed: no)  
When the description states that a distinct activity occurs between a preceding process stage and a later activity: Model the activity as a separate task and connect it to the preceding and following flow in the stated order.

**LRN-039** (T5; refines FLOW-07; 2 description(s); confirmed: yes)  
When the description says an optional activity may occur after an outcome, and each occurrence is followed by another specified activity: Model the optional activity as a task on one branch of an exclusive gateway, with the other branch ending or continuing as described; connect the activity back to the specified later activity when it must follow each occurrence.

**LRN-043** (T5; refines GW-01; 2 description(s); confirmed: yes)  
When the description presents mutually exclusive alternatives selected according to a stated condition: model an exclusive gateway to route the process into the applicable alternative, with outgoing flows reflecting the stated conditions

**LRN-050** (T7; refines COL-04; 2 description(s); confirmed: no)  
When the description states that one participant’s described activity or occurrence communicates information or an item to another participant: Model the described activity or occurrence itself as the appropriate message-flow endpoint: use a task for performed work and an event for an occurrence. Do not add a separate send task merely to carry the same communication.

**LRN-051** (T5; refines FID-02; 2 description(s); confirmed: no)  
When the description explicitly orders process steps, including steps separated by a waiting condition or event: Connect the corresponding BPMN elements with sequence flows in the described order, keeping any intervening events in the flow.

**LRN-052** (T5; refines FID-01; 2 description(s); confirmed: yes)  
When the description states that a participant performs a distinct action between other steps: Model the action as its own activity and connect it to the preceding and following steps with sequence flows in the described order.

**LRN-055** (T5; refines ACT-07; 2 description(s); confirmed: no)  
When the description states that the outcome of an activity determines which continuation applies: Connect the activity to a decision gateway and route each outgoing branch to the corresponding next step or ending.

**LRN-057** (T5; refines ACT-04; 2 description(s); confirmed: no)  
When the description states that a participant must send a report or other information to a recipient: model the reporting action itself as a send task when sending the information is the work being performed, rather than as a generic service task

**LRN-063** (T5; refines FLOW-07; 2 description(s); confirmed: no)  
When the description says an activity is repeated until a stated condition is met: Model each attempt followed by a decision; loop back to repeat the activity when the condition is not met, and continue when it is met.

**LRN-066** (T5; new; 2 description(s); confirmed: no)  
When the description says a person must choose or specify inputs before automated work begins: Model that choice or specification as a user task before the automated work.

**LRN-091** (T6; refines FID-03; 2 description(s); confirmed: no)  
When the description identifies an activity by its action and object, or distinguishes it from neighboring activities: Label the BPMN activity with the action and object supported by the description; do not substitute an inferred action or fold a neighboring activity into its label.

**LRN-001** (T5; refines FID-02; 1 description(s); confirmed: yes)  
When the description distinguishes an action that occurs before a later recording, confirmation, or other outcome: Model that action as a distinct activity in the sequence; do not omit it or use a terminal outcome event as its substitute.

**LRN-004** (T5; refines EVT-01; 1 description(s); confirmed: yes)  
When the description states that an external request or inquiry starts the process: Model the trigger as a start event, followed by a distinct task for receiving or handling the request.

**LRN-011** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description explicitly states that a later phase begins after an earlier outcome and names activities that belong to that phase: model the stated phase initiation as a distinct task before its activities, connected to the flow for the outcome that starts the phase

**LRN-014** (T5; refines ACT-05; 1 description(s); confirmed: yes)  
When the description presents receipt of a physical item as a process step, rather than explicitly describing a wait for a message, signal, time, or condition: Model the receipt as a task, not an intermediate catch event.

**LRN-015** (T5; refines ACT-07; 1 description(s); confirmed: yes)  
When the description says that an item is placed in one of multiple alternative destinations: Model the alternatives with an exclusive gateway and a separate task for each destination, rather than one combined task.

**LRN-016** (T5; refines GW-04; 1 description(s); confirmed: no)  
When the description makes completion contingent on both a time-based condition and a separate required activity, without stating that one must precede the other: Model the time-based wait with an intermediate catch event and the activity as a parallel branch; synchronize the branches with a parallel gateway before completion.

**LRN-018** (T5; refines GW-02; 1 description(s); confirmed: no)  
When the description says an additional activity may be performed before a later activity that follows regardless: Model the additional activity as a distinct optional path that rejoins the main flow before the later shared activity.

**LRN-021** (T1; refines XML-06; 1 description(s); confirmed: yes)  
When the description calls for a BPMN model containing gateways, events, or other flow elements: Ensure the generated BPMN XML conforms to BPMN20.xsd: declare default flows on gateways rather than sequence flows, and assign every element a valid, unique XML ID.

**LRN-022** (T6; refines FID-03; 1 description(s); confirmed: yes)  
When the description presents multiple alternative ways to perform one activity: Label the BPMN activity at a level of generality that preserves the alternatives rather than selecting only one.

**LRN-023** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description identifies multiple distinct criteria for evaluating an item: Model each criterion as a distinct assessment activity rather than subsuming them in one generic assessment activity.

**LRN-024** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description identifies alternative terminal outcomes and states an action associated with at least one outcome: Model each outcome on its own branch, representing any stated action that realizes an outcome as a task before a terminal end event.

**LRN-027** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a participant may perform an optional activity after the main process outcome has been reached: Model that activity as an optional continuation of the same process, rather than as a new process initiated by the activity.

**LRN-028** (T5; refines ACT-07; 1 description(s); confirmed: yes)  
When the description states that an output may be checked more than once and that the results may require changes: Model the check and any resulting changes as explicit activities. Use a decision gateway to determine whether another check is needed, and route changed work back to the check.

**LRN-029** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states distinct activities in sequence and indicates that later work may be repeated or changed in response to earlier results, without naming a separate activity for communicating those results: Model the stated activities in order, represent repetition with a decision and return flow, and treat results as information unless a distinct communication activity is explicitly stated.

**LRN-030** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description specifies multiple distinct actions within one activity: label the BPMN activity so that it communicates each stated action, rather than omitting one

**LRN-031** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description specifies an ordered sequence of checks, allows work to be revised based on their results, and requires approval of revisions: model the checks in the stated order, route each revision through any stated required approval, and use a decision with a return flow to repeat the relevant checks before proceeding to final approval or another outcome

**LRN-032** (T5; refines ACT-05; 1 description(s); confirmed: yes)  
When the description states that work is performed after a preparation or readiness stage: Model the performed work as a distinct activity/task in the sequence; do not represent readiness for that work as an event in its place.

**LRN-033** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a reviewer examines a process or other work and identifies findings: Model the examination as a distinct activity; do not represent only the findings or omit the examination.

**LRN-035** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a condition starts a distinct phase and separately names activities included in that phase: Model the conditional branch to the phase-start activity or subprocess, then represent the included activities within that phase rather than using one of them as the branch target.

**LRN-037** (T5; refines ACT-05; 1 description(s); confirmed: no)  
When the description states that a report or message from an external participant conditionally triggers a continuation within an already-running process: Model receipt of the report as an intermediate message catch event in the existing process, rather than as a task or a new start event.

**LRN-038** (T6; refines ACT-04; 1 description(s); confirmed: no)  
When the description says that a participant receives a communication or deliverable without separately naming the provider’s action: Model the implied delivery from the responsible provider’s perspective as sending or providing the item, rather than modeling receipt as that participant’s work.

**LRN-040** (T5; refines FLOW-07; 1 description(s); confirmed: no)  
When the description states that an activity may recur whenever a specified event occurs, and that each recurrence is followed by another activity: Model the recurrence with a decision and a return flow that lets the subsequent activity happen again, while providing a meaningful way to exit the cycle.

**LRN-041** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description distinguishes receiving proposals or offers from choosing among them: Model the choice as a separate activity rather than treating receipt of a proposal or offer as the choice.

**LRN-042** (T7; refines FID-01; 1 description(s); confirmed: no)  
When the description states that an item is prepared for collection or transfer once the required prerequisites are ready: Model the preparation as an activity, rather than treating readiness only as a state or omitting the step; when it completes the described process outcome, represent that completion with an end event.

**LRN-044** (T7; refines COL-01; 1 description(s); confirmed: yes)  
When the description identifies multiple external organizations as interchangeable candidates for the same interaction and says that one is selected: Model the candidates collectively as one external participant, rather than creating a separate pool and message flow for each candidate.

**LRN-045** (T5; refines EVT-03; 1 description(s); confirmed: no)  
When the description says that reaching a deadline can determine which continuation occurs, while other outcomes may also occur first: Model the wait for the deadline as a timer intermediate catch event, using an event-based gateway when the deadline competes with other catching outcomes.

**LRN-047** (T5; refines EVT-03; 1 description(s); confirmed: no)  
When the description states that an initial attempt may remain unresolved, identifies a notification and further processing before information is returned: Model the notification, further processing, and return of information as distinct steps on the delayed path; in the receiving process, wait for the information with a message catch event.

**LRN-048** (T5; new; 1 description(s); confirmed: no)  
When the description says that, after a request, either a response or a notification that further processing is needed may be received first: Model the competing message arrivals with an event-based gateway targeting message-catching events; if the notification leads to another response, model the subsequent wait with a separate message-catching event.

**LRN-049** (T3; refines ACT-07; 1 description(s); confirmed: yes)  
When the description states that one step follows another without describing a branch or synchronization at that point: Connect the steps directly rather than inserting a gateway with one incoming and one outgoing sequence flow.

**LRN-053** (T3; refines EVT-04; 1 description(s); confirmed: no)  
When the description states that access to information is restricted until a specified duration has elapsed: Model the wait with an intermediate timer catch event in the process flow, and connect it by an outgoing sequence flow to the continuation that permits access.

**LRN-054** (T5; refines ACT-08; 1 description(s); confirmed: no)  
When the description explicitly requires a human participant to carry out an activity: Model that activity as a user task rather than a generic task.

**LRN-056** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that an activity is carried out over a period and that a decision about whether to continue it is made at the end of that period: model the period of carrying out the activity as an activity before the continuation decision

**LRN-058** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description gives an activity or decision a meaningful qualifier, such as its recipient, scope, timing, or eligibility criteria: Preserve meaningful qualifiers in the BPMN task label or gateway question; do not broaden or narrow the stated action or decision.

**LRN-059** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says a participant can enter or provide information before later process actions: Model the information-entry step as an activity, not as a start event.

**LRN-060** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description says that a resource must be arranged by reaching an agreement with another party: Model identifying a suitable option as a distinct activity before reaching the agreement, and connect the activities in that order.

**LRN-061** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description says to check whether required items are available and specifies a follow-up if any are unavailable: Model the check as an exclusive decision gateway with conditional flows for the available and unavailable outcomes, routing the unavailable outcome to the stated corrective activity.

**LRN-064** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description groups multiple values or attributes within a single activity, such as details to enter or options to select: Label the BPMN activity with its core action and object rather than enumerating every value, unless distinguishing those values is necessary to identify separate modeled steps.

**LRN-065** (T5; refines GW-06; 1 description(s); confirmed: no)  
When the description says that an event or milestone can change the route during work, or that completion makes follow-up actions available: Model the supported outcomes as connected conditional branches, using a suitable gateway for the stated choice; when flow waits for an event or other trigger, model the wait with an intermediate catch event.

**LRN-067** (T7; refines LANE-01; 1 description(s); confirmed: no)  
When the description assigns work within one process to both a human user and an automated system acting for that user: Use separate lanes to show their respective responsibilities and assign each described activity to the responsible lane.

**LRN-068** (T5; new; 1 description(s); confirmed: yes)  
When the description says that information is sent to an external participant and that revisions or acceptance depend on the participant’s response: Model the stated send-and-receive communications in sequence, and represent the repeated exchange with a return flow and an explicit decision about whether to continue.

**LRN-069** (T5; refines GW-02; 1 description(s); confirmed: no)  
When the description makes a later activity depend on the outcome of an evaluation and specifies a different response for the other outcome: model an exclusive gateway before the later activity to route each outcome to its corresponding path

**LRN-070** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description says a participant chooses one option from several alternatives: Model the choice with an exclusive gateway and route each alternative to its corresponding activity using conditional sequence flows.

**LRN-071** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description states that work can start upon the first of several expected occurrences, without waiting for the others: Model the first occurrence as a trigger for the work, while allowing the remaining expected occurrences to proceed concurrently; do not synchronize all occurrences before starting the work.

**LRN-072** (T5; refines ACT-07; 1 description(s); confirmed: yes)  
When The description states that one activity is carried out while the result of an already-started activity is still pending: Model the pending result with an intermediate catch event on one parallel branch and the concurrent activity on another; synchronize the branches before later work that depends on both.

**LRN-073** (T6; new; 1 description(s); confirmed: no)  
When the description says a system or other participant gives, displays, or makes information or options available to another participant: model the activity from the provider’s perspective as presenting or providing them, rather than as the recipient’s act of receiving them

**LRN-074** (T3; refines PROC-05; 1 description(s); confirmed: yes)  
When When the description states that an event can end a process that is already in progress:: Model the event as an interrupting catch event in the existing process scope, with a path to a reachable end event; do not model it as an additional process start.

**LRN-075** (T5; refines FLOW-07; 1 description(s); confirmed: no)  
When the description states that an ongoing process is paused and later resumed, after which previously ongoing work continues: Model an explicit sequence flow from the resumption to the work that continues, making the resumed work clear.

**LRN-076** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description states a threshold or cutoff but does not specify a number: Model the decision and its branch conditions without adding a numeric threshold that the description does not provide.

**LRN-077** (T6; refines ACT-04; 1 description(s); confirmed: no)  
When the description says a process collects information from a source to calculate a result, without describing waiting for an incoming message: model the collection as performed work rather than as a receive task

**LRN-078** (T6; new; 1 description(s); confirmed: no)  
When the description states that a decision depends on earlier outcomes but does not identify a particular criterion for that decision: Label the gateway using only the stated dependency; do not add a specific test, threshold, or criterion that the description does not provide.

**LRN-079** (T5; refines EVT-03; 1 description(s); confirmed: yes)  
When the description says that a participant is expected to arrive at an unspecified or random time after an activity: Model waiting for that arrival as an intermediate catch event, not as an event-based gateway.

**LRN-080** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that an activity may be left incomplete when a required resource is unavailable, and describes a consequence or next step for that case: model the completed and incomplete outcomes as distinct conditional paths; route only the completed outcome to activities that depend on completion, and represent the next step for the incomplete outcome as described.

**LRN-082** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a participant obtains a choice between alternatives that determine the process path: Model an activity representing the choice being obtained before a gateway that routes the selected alternative.

**LRN-083** (T5; refines GW-05; 1 description(s); confirmed: no)  
When the description states that a process begins with a received order, then obtains a choice, and that selected work includes required concurrent activities before a later activity: Connect the start event to the activity that obtains the choice, route the alternatives through a decision gateway, and, where the selected path requires concurrent work, use a parallel split and join before the later activity.

**LRN-084** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a sequence of activities repeats until a completion condition is met, and then describes subsequent work: Model a decision at the completion check, route the incomplete outcome back to the repeated activities, and connect the completed outcome to the subsequent work.

**LRN-085** (T6; refines EVT-03; 1 description(s); confirmed: no)  
When the description says that the process waits for an external participant to confirm or respond: Model receipt of that confirmation or response as an intermediate message catch event, not as a task.

**LRN-086** (T5; refines FLOW-04; 1 description(s); confirmed: yes)  
When the description makes a follow-up action depend on whether a stated duration threshold was exceeded during a wait, and the wait completes before the continuing work proceeds: Model an exclusive decision after the wait, route the threshold-dependent action on its conditional branch, and merge that branch with the continuing route before later work. Do not represent the condition solely as a boundary event on the waiting activity.

**LRN-087** (T5; new; 1 description(s); confirmed: no)  
When the description says an initial item is checked, and when a completion condition is not met, another item is selected before the same check is repeated: Route the initial entry and the repeat path through a shared merge gateway before the repeated check, keeping the item-selection activity on the repeat path. Route the completed outcome to the subsequent work described.

**LRN-088** (T5; new; 1 description(s); confirmed: no)  
When the description says that an application or other automated system presents information or options to a participant: Model the presentation as a separate service task performed by the system, rather than omitting it or modeling only the participant’s subsequent choice.

**LRN-089** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states an activity and separately states that its duration or performance is measured: Model the measurement as a distinct activity, and connect it to the measured activity according to the temporal relationship stated in the description.

**LRN-090** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description makes continuation depend on a decision and states distinct outcomes, including one that ends the process and one that continues: Model a separate outgoing sequence flow for each stated outcome, connecting each to its described termination or continuation.

**LRN-092** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description requires multiple activities to be completed but permits them in any order, and describes a check after each activity that determines whether further work or completion follows: Model routing that allows every required activity to occur in a permitted order, include the described check after each activity, and route its outcomes to either further work or completion.

**LRN-093** (T6; refines FID-02; 1 description(s); confirmed: no)  
When the description distinguishes initiating or submitting a request from registering it before a later participant receives or handles it: model the initiation or submission and registration as separate activities, preserving their stated order before routing the request onward

**LRN-094** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description presents two or more outcomes as mutually exclusive alternatives: Model an exclusive gateway that selects the applicable alternative, with each branch leading to its corresponding outcome.

**LRN-095** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that a participant performs an action to communicate a response after an assessment, with the response depending on the assessment result: model the response as a distinct activity following the assessment, and represent any stated response alternatives

**LRN-096** (T5; refines COL-03; 1 description(s); confirmed: no)  
When the description explicitly orders an interaction in which one participant sends information, another participant acts on it, and a response follows: Model the sending, the recipient's action, and the response in the stated causal order, using message flows between participants and sequence flows within each participant's process.

**LRN-097** (T5; refines ACT-07; 1 description(s); confirmed: yes)  
When the description says that a condition may send the flow back to an earlier activity that must be performed again: model the initial route and return route(s) as converging at a merge gateway before that repeated activity

## Example-specific guidelines

**EXS-002** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a successful outcome includes concrete actions or adjustments: Model each explicitly stated action or adjustment as part of the outcome; do not infer parallel branches unless the description establishes concurrent or independently required work.

**EXS-003** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that an item may be reviewed more than once and that review feedback can lead to changes: Model feedback and resulting changes as explicit activities. Use a decision gateway to determine whether another review is needed, and route changed work back to the relevant review.

**EXS-014** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description asks for help organizing distinct matters and explicitly mentions negotiation: Model each explicitly named matter as a separate BPMN activity, including the stated negotiation; do not infer additional steps beyond what the description supports.
