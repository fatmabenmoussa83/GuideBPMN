# Learned guidelines: GPT-6 Luna, Revised, run 2

94 generic and 0 example-specific error-driven guidelines; 46 generic guidelines confirmed. Full records (evidence, confirmation tests, provenance): `learned_guidelines.json`.

## Generic guidelines

**LRN-060** (T6; refines FID-03; 18 description(s); confirmed: yes)  
When the description states a specific activity, decision, or outcome: Label the corresponding BPMN element with wording that preserves the described action and its object or result; do not substitute a related but different action or outcome.

**LRN-015** (T6; refines FID-03; 15 description(s); confirmed: yes)  
When the description names an activity or outcome with multiple stated actions, alternatives, or a distinguishing object or participant: Label the corresponding BPMN activity or event so its described scope remains identifiable. Preserve materially stated actions, alternatives, and objects or participants; do not substitute a broader or different action or add unsupported details.

**LRN-003** (T5; refines ACT-07; 12 description(s); confirmed: yes)  
When the description identifies multiple required activities within a phase, requires all of them before that phase can end, and specifies no order among them: Model the activities as parallel branches synchronized by a parallel gateway.

**LRN-042** (T5; refines FLOW-01; 12 description(s); confirmed: yes)  
When the description presents activities in an order, states a decision outcome that leads to an activity, or identifies an event that determines what happens next: Connect each stated transition with a sequence flow, including from the start event to the first activity, from each decision branch to its specified next step, and from an event-based gateway to its catching-event target.

**LRN-010** (T5; refines EVT-01; 7 description(s); confirmed: yes)  
When the description says a process begins when a participant performs an identifiable action that establishes the process trigger: Model a start event for the trigger, followed by a separate task for the participant’s action; do not represent the action only as a start event.

**LRN-001** (T6; refines FID-01; 6 description(s); confirmed: no)  
When the description distinguishes different actions or process states involving the same participant or subject at different stages: Label each BPMN activity and outcome to reflect the specific action or state described at that stage; do not substitute a different action or an unsupported outcome.

**LRN-031** (T5; refines ACT-07; 6 description(s); confirmed: yes)  
When the description states that an activity is followed by a decision, synchronization, or cycle-exit condition, or that concurrent work begins after a preceding activity: Connect the activity to the relevant gateway with a sequence flow; for concurrent work, route the preceding flow through a parallel gateway that starts the concurrent branches.

**LRN-005** (T6; refines FID-03; 5 description(s); confirmed: no)  
When the description states a meaningful condition or outcome that starts or ends the process: Label the corresponding start or end event with that condition or outcome rather than a generic label.

**LRN-022** (T6; refines FID-03; 5 description(s); confirmed: yes)  
When the description states a specific business trigger or process outcome for a start or end event: Label the corresponding BPMN event with a concise phrase that preserves that stated trigger or outcome, rather than using a generic label such as “start” or “end”.

**LRN-004** (T5; refines FID-01; 4 description(s); confirmed: yes)  
When the description states a process start and an ordered sequence of activities or transitions between phases: Model the stated start, include each distinct activity, and connect the flow nodes with sequence flows in the described order, including transitions between phases.

**LRN-006** (T5; refines GW-01; 4 description(s); confirmed: yes)  
When the description states that an action has mutually exclusive alternatives for how or where it is carried out: Model the choice with an exclusive gateway and a separate task for each alternative.

**LRN-007** (T6; refines FID-01; 4 description(s); confirmed: yes)  
When the description lists multiple distinct actions to be performed in sequence, including actions within one process stage: Model each distinct action as a separate BPMN activity and connect the activities in the described order; do not omit an action because it appears in a list.

**LRN-009** (T5; refines EVT-13; 4 description(s); confirmed: no)  
When the description says that the process waits for a stated time or period to end before continuing: Model the wait as an intermediate catch timer event, then connect it to the subsequent activity rather than representing the passage of time as a task.

**LRN-016** (T5; refines ACT-07; 4 description(s); confirmed: yes)  
When the description states that a process has a completion point but an optional activity may occur afterward: Model an exclusive gateway that routes either through the optional activity and then to an appropriate end event, or directly to that end event.

**LRN-021** (T5; refines ACT-07; 4 description(s); confirmed: yes)  
When the description says that an activity continues while a milestone or other condition is pending, and that a later phase follows once the condition is met: Model a decision point after the activity: route the unmet outcome back to repeat the activity and the met outcome to the later phase.

**LRN-026** (T3; refines COL-01; 4 description(s); confirmed: yes)  
When the description states that one participant requests information or action from another participant and that the other participant provides a response: Model the request and response as a connected interaction: use sequence flows within a participant’s process and message flows between distinct participant pools, rather than an unrelated detached start-to-end chain.

**LRN-036** (T6; refines FID-03; 4 description(s); confirmed: yes)  
When the description explicitly identifies the role or participant responsible for an activity: Include that responsible role or participant in the BPMN activity label when needed to preserve who performs the work.

**LRN-051** (T5; refines ACT-07; 4 description(s); confirmed: no)  
When the description states that an activity's result or a condition determines which of multiple alternative paths follows: Connect the activity to an exclusive gateway and model each alternative as a separate outgoing branch.

**LRN-011** (T6; refines FID-03; 3 description(s); confirmed: yes)  
When the description states a core activity and separately describes a condition or later outcome that marks its completion: Label the BPMN activity with its core action and object; do not add the separately stated completion condition or later outcome to the activity label.

**LRN-041** (T6; new; 3 description(s); confirmed: no)  
When the description states a condition that distinguishes alternative branches: Label the gateway with the branch-controlling condition stated in the description, rather than with a separate downstream decision or activity.

**LRN-048** (T5; refines FID-01; 3 description(s); confirmed: yes)  
When the description explicitly states an action performed by a participant before subsequent process work: Model that action as a BPMN activity and include it in the sequence flow.

**LRN-059** (T6; refines FID-03; 3 description(s); confirmed: yes)  
When the description states a condition or outcome that a decision assesses: Label the corresponding BPMN gateway with a concise question that identifies that condition or outcome, rather than using a generic participant-response label or substituting a different decision.

**LRN-008** (T6; refines FID-03; 2 description(s); confirmed: yes)  
When the description gives contextual details or examples alongside a single activity, without presenting them as separate actions: label the BPMN task with its core action and object; omit contextual details and qualifiers that are not needed to identify the activity

**LRN-012** (T5; refines FID-01; 2 description(s); confirmed: no)  
When the description states that an additional activity may be performed: Model that activity on an optional branch, preserving its connection to the subsequent flow.

**LRN-013** (T5; refines FID-02; 2 description(s); confirmed: yes)  
When the description presents multiple distinct activities as optional alternatives: Model each activity separately on an appropriate branch, rather than combining the alternatives into one activity, and preserve their connection to the subsequent flow.

**LRN-017** (T5; refines ACT-07; 2 description(s); confirmed: no)  
When the description states that a process can end in one of multiple mutually exclusive outcomes: Model an exclusive gateway with a separate branch for each outcome, leading to the corresponding modeled outcome.

**LRN-020** (T5; refines FID-02; 2 description(s); confirmed: no)  
When the description says an activity occurs repeatedly or continues over an ongoing process and separately states that another activity starts only when a condition occurs: do not model the ongoing activity as an unconditional predecessor of the condition-triggered activity; preserve their distinct timing and stated dependencies in the BPMN flow

**LRN-024** (T5; refines FID-01; 2 description(s); confirmed: yes)  
When the description says that feedback from reviews may prompt repeated changes to a proposed outcome: Model feedback handling as a distinct activity, then use a decision point to route the flow through the relevant change and review work again when needed, or onward when no further change is needed.

**LRN-027** (T5; refines FID-01; 2 description(s); confirmed: yes)  
When the description explicitly states an activity that occurs only under a condition or as part of a repeated cycle: Model the activity on the applicable conditional branch or in the repeated flow, preserving its stated place and dependencies in the process.

**LRN-037** (T5; refines ACT-05; 2 description(s); confirmed: yes)  
When the description states that an external participant performs an action that initiates work by another participant: Model the action as a task in the external participant’s process and connect it to the receiving participant’s process with a message flow.

**LRN-038** (T5; refines FID-01; 2 description(s); confirmed: yes)  
When the description states that a participant selects one option from multiple offers or alternatives: Model the selection as an explicit activity performed by that participant; do not represent the selection only through a gateway or route condition.

**LRN-043** (T6; refines FID-03; 2 description(s); confirmed: no)  
When the description presents a decision whose possible outcomes are stated as conditions or answers: Label the corresponding gateway with a concise question that expresses the described decision, rather than a generic label that does not identify what is being decided.

**LRN-049** (T7; refines COL-04; 2 description(s); confirmed: yes)  
When the description assigns actions to distinct participants and describes information, requests, or responses passing between them: Model each independent participant in a separate pool and represent each described communication with a message flow from sender to receiver, using valid interaction nodes or participant boundaries.

**LRN-061** (T5; refines ACT-07; 2 description(s); confirmed: yes)  
When the description says that one activity can be carried out while another activity or sequence of activities is underway, and that both tracks must be complete before a later activity can proceed: Model the tracks as concurrent branches, using a parallel gateway to split them and a parallel gateway to synchronize them before the dependent activity.

**LRN-070** (T5; refines FID-02; 2 description(s); confirmed: no)  
When the description states that activities have an order or repetition, or that work happens concurrently: Model the stated order and repetition with sequence flows and loops, and model concurrent work with appropriate gateways, preserving the described dependencies.

**LRN-071** (T5; refines FID-01; 2 description(s); confirmed: no)  
When the description states distinct participant actions and their order, or describes outcomes that determine subsequent paths: Model each stated action as a corresponding BPMN activity, connect activities in the stated order, and represent outcome-dependent paths with appropriate gateways and flows.

**LRN-083** (T5; refines FID-01; 2 description(s); confirmed: yes)  
When the description states that a participant checks whether a completion condition has been met before the process can proceed: Model the check as a distinct activity performed by that participant, followed by a decision gateway whose condition routes the flow back to the relevant earlier steps or onward when the condition is met.

**LRN-090** (T5; refines ACT-08; 2 description(s); confirmed: no)  
When the description says that an actor sends or forwards an item to another actor, but does not describe message communication as the work being performed: Model the action as an ordinary task rather than inferring a send-task subtype from the sending verb alone; use a send task when the description establishes that sending a message is itself the modeled work.

**LRN-002** (T5; refines EVT-03; 1 description(s); confirmed: no)  
When the description says that a process may continue only after an external participant approves a proposal: Model the approval wait as an intermediate catch event after the proposal is provided and before the dependent activity; preserve that order rather than modeling the wait as a task.

**LRN-014** (T5; refines GW-03; 1 description(s); confirmed: no)  
When the description states that a process can begin through alternative channels before continuing through a shared flow: Model each channel as a separate branch and merge the branches with an exclusive gateway before the shared flow.

**LRN-018** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description states a condition for proceeding but does not state what happens otherwise: Do not label an end event with an inferred negative outcome; use a neutral label unless the description supports a specific outcome.

**LRN-019** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says a request is evaluated against stated criteria before an approval decision: Model the evaluation as a separate activity before the approval decision.

**LRN-023** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says that reaching a terminal state requires a concrete action or transition to that state: Model the action or transition as an activity before an end event; use the end event only to mark completion.

**LRN-025** (T6; refines FID-02; 1 description(s); confirmed: no)  
When the description distinguishes preparatory work from a subsequent review and describes findings identified during that review: Model the review as a separate activity before modeling the activity that records or addresses its findings.

**LRN-028** (T5; refines FLOW-01; 1 description(s); confirmed: yes)  
When the description says that one activity uses or examines something produced by another activity: Connect the corresponding BPMN flow nodes with a sequence flow in the stated order.

**LRN-029** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description states that a downstream activity can begin only after multiple prerequisite activities are complete: join the prerequisite paths with a parallel gateway, then connect that gateway to the dependent activity with a sequence flow

**LRN-030** (T1; refines XML-03; 1 description(s); confirmed: yes)  
When the description calls for a process model that will be serialized as BPMN XML: Give every BPMN element an identifier that satisfies the XML Schema ID lexical rules and is unique within the model.

**LRN-032** (T5; refines GW-04; 1 description(s); confirmed: no)  
When the description states that multiple required actions follow a condition, without specifying an order between them: Model the actions as separate branches from a parallel split.

**LRN-033** (T6; refines ACT-04; 1 description(s); confirmed: yes)  
When the description says that goods or services are delivered but does not describe sending a message to another participant: Model the delivery as a generic task, not a send task.

**LRN-034** (T5; new; 1 description(s); confirmed: yes)  
When the description says an optional activity may occur after a later activity, and that each occurrence causes that later activity to happen again: Model the optional activity on a conditional return path to the later activity, while preserving the path that continues without the optional activity.

**LRN-035** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description says an activity may be postponed because the participant has competing work: Model and label the delay as postponing the stated activity; do not describe it as performing the competing work.

**LRN-039** (T7; refines LANE-01; 1 description(s); confirmed: yes)  
When the description assigns work to multiple internal roles or departments within one process and also describes interaction with an outside participant: Model the internal responsibilities as lanes within the same process pool; model the outside participant separately only when the description establishes independent communication.

**LRN-040** (T5; refines GW-06; 1 description(s); confirmed: yes)  
When the description states that an activity is required while another activity may be performed only if a stated condition holds, and that the flow continues after the applicable work is complete: Model the activities as branches from an inclusive split, with the condition on the optional branch, and use an inclusive join to synchronize the branches that were activated before the dependent next step.

**LRN-044** (T7; new; 1 description(s); confirmed: yes)  
When the description identifies an outside person or organization as the destination of a handoff but describes no subsequent action or response by that recipient: Model the handoff as an activity in the modeled process; do not add a separate participant pool and message flow solely because the recipient is named.

**LRN-045** (T6; new; 1 description(s); confirmed: no)  
When the description states that a participant’s response or communication causes the process to continue to subsequent work: Label the corresponding intermediate catch event as the receipt or occurrence of that response, rather than as an action performed by the participant.

**LRN-046** (T5; refines GW-07; 1 description(s); confirmed: no)  
When the description says an external participant may report that an outcome is pending before providing that outcome: Model the immediate outcome and pending-status message as alternative incoming communications selected by an event-based gateway; after the pending notification, model a separate catch event for the eventual outcome, and model sending the outcome after the relevant processing paths converge.

**LRN-047** (T7; refines COL-01; 1 description(s); confirmed: no)  
When the description identifies a user-facing software interface as a recipient of information produced by a process and describes that information being communicated to the interface: Model the interface as a separate participant pool and represent the exchange with message flows between that pool and the process; do not model the exchange solely as internal events or activities.

**LRN-050** (T6; refines FID-03; 1 description(s); confirmed: yes)  
When the description distinguishes the condition that initiates a process from a later request, order, or milestone: Label the start event with the initiating condition, not the later milestone.

**LRN-052** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that one activity must happen before another: Model the activities with sequence flows in the stated order, not as concurrent branches.

**LRN-053** (T6; refines QA-04; 1 description(s); confirmed: no)  
When the description states a decision or activity but does not specify an alternative outcome: Label the corresponding BPMN activity without adding an alternative outcome that the description does not state.

**LRN-054** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description assigns separate notification duties to different recipients, with each duty applying to a distinct qualifying event or time limit: Model each notification as a separate activity, and connect it only to the branch where its stated qualification is met, preserving any stated deadline.

**LRN-055** (T6; refines FID-03; 1 description(s); confirmed: yes)  
When the description states a decision whose outcome depends on multiple explicit eligibility criteria: Label the corresponding BPMN gateway or its outgoing flows so that the decision-relevant criteria are preserved; do not broaden the decision by omitting a stated qualification.

**LRN-056** (T5; new; 1 description(s); confirmed: no)  
When the description states that distinct reporting duties apply independently or that more than one duty may be required for the same event: Model each duty as a separate activity on its own conditionally activated path, so all applicable duties can be performed rather than treating them as mutually exclusive alternatives.

**LRN-057** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description specifies a meaningful constraint on an activity, such as its quantity or frequency: Preserve that constraint in the BPMN activity label rather than using a broader label that omits it.

**LRN-058** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description enumerates prerequisites or supporting materials for a formal application: model the stated preparation of those prerequisites as distinct activities before the application is submitted, and retain any explicitly described review as a separate activity.

**LRN-062** (T5; refines GW-01; 1 description(s); confirmed: no)  
When the description says that one or more of several optional actions may be selected, including that multiple actions may be performed together: Model the alternatives with an inclusive gateway so any nonempty combination of the actions can proceed.

**LRN-063** (T7; refines LANE-01; 1 description(s); confirmed: no)  
When the description assigns work to both a human and an automated system within the same process: Represent each stated responsibility in the BPMN model, using lanes to distinguish the human and automated work and assigning activities to the appropriate lane.

**LRN-064** (T5; refines EVT-01; 1 description(s); confirmed: no)  
When the description states that a notification or milestone can occur after process work has begun: Model the later trigger within the ongoing process as an intermediate catch event, not as an independent process start event.

**LRN-065** (T5; refines EVT-03; 1 description(s); confirmed: no)  
When the description says that work or a proposal is sent to an external participant, then feedback is expected before deciding whether the outcome is satisfactory: Model the wait for feedback as an intermediate message catch event before the satisfaction decision, and route an unsatisfactory outcome back through the change-and-resubmission cycle.

**LRN-066** (T5; new; 1 description(s); confirmed: yes)  
When the description says that several work items must each pass an evaluation before a later step can proceed, and that unsuccessful items require revision and another evaluation: Model an outcome decision for each work item, route unsuccessful items through the required revision and back to evaluation, and synchronize the successful paths before the dependent step.

**LRN-067** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description requires querying every relevant provider to gather comparable information before deciding what to obtain: Model the inquiries and the comparison as distinct activities, placing the comparison after the inquiries and before selection or ordering.

**LRN-068** (T6; refines ACT-05; 1 description(s); confirmed: no)  
When the description says that an occurrence or incoming item triggers subsequent work, rather than describing work performed by the process: Model that trigger as an intermediate catch event, not as a task to wait for or receive the item.

**LRN-069** (T5; refines ACT-04; 1 description(s); confirmed: yes)  
When the description says a participant initiates an order or request, then describes its processing while other work is performed: Model the initiation as an activity, represent waiting for completion as an intermediate catch event, and use a parallel gateway to start the concurrent work.

**LRN-072** (T5; refines PROC-05; 1 description(s); confirmed: no)  
When the description says that work resumes after an external restart: Model the restart as an intermediate catch event and connect it by sequence flow to the activity that resumes the ongoing work.

**LRN-073** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description says that information is collected from an external device or system for use in a later calculation: Model the information retrieval as a distinct activity before the calculation, and use an appropriate BPMN task type for the described retrieval.

**LRN-074** (T6; refines FID-04; 1 description(s); confirmed: no)  
When the description states a decision cutoff but does not specify its numeric amount: Preserve that level of specificity in the BPMN gateway label or condition; do not invent a precise threshold.

**LRN-075** (T5; refines ACT-03; 1 description(s); confirmed: no)  
When the description distinguishes human-performed interactions from automated collection or presentation of information: Model them as separate BPMN activities and use a service task for the automated work.

**LRN-076** (T5; refines EVT-03; 1 description(s); confirmed: yes)  
When the description says an external participant is expected to arrive at an unspecified time: Model the wait for that arrival as an intermediate catch event before the subsequent work.

**LRN-077** (T1; refines EVT-05; 1 description(s); confirmed: yes)  
When the description says the flow waits until a condition becomes true before continuing: Model the wait as a conditional intermediate catch event and include the condition expression in its conditionalEventDefinition.

**LRN-078** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says that a participant may choose whether to perform an optional action after the main work is complete: Model the choice with an exclusive gateway: one branch performs the optional action, and the other bypasses it. Ensure both paths can reach an appropriate process end.

**LRN-079** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that attempted work may remain incomplete when a prerequisite is unavailable, and that the work is resumed after the prerequisite is obtained: Model a decision after the attempt: route the completed outcome to the next step, and route the incomplete outcome through obtaining the prerequisite and any required rescheduling before returning to the relevant work.

**LRN-080** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description makes a later action depend on a condition being met, but does not describe an activity that performs that condition: Model the condition as a decision gateway with flows for the possible outcomes; do not add an activity that performs the condition in place of the gateway.

**LRN-081** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description states that a participant incurs a penalty or other consequence: Model the imposition of that consequence as a BPMN activity, rather than representing it only as an end event.

**LRN-082** (T1; refines EVT-14; 1 description(s); confirmed: no)  
When the description calls for communication modeled with a BPMN message event and the model includes a message reference: Encode the reference as the schema-defined messageRef attribute on the bpmn:messageEventDefinition; do not serialize it as a child XML element.

**LRN-084** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description qualifies an activity with a condition that distinguishes when it applies or which variant it represents: Include that material qualification in the BPMN activity label so the described distinction remains identifiable; do not use a generic label that omits it.

**LRN-085** (T5; refines EVT-03; 1 description(s); confirmed: yes)  
When the description says the process must wait for an occurrence and makes a subsequent action depend on whether the wait exceeded a stated duration: Model the wait for the occurrence with an intermediate catch event, then use an exclusive gateway to evaluate the elapsed-time condition and route the qualifying branch to the action.

**LRN-086** (T5; new; 1 description(s); confirmed: yes)  
When the description presents multiple distinct activities after a shared preceding activity without stating that they are alternatives or specifying an order between them: Model the activities as separate concurrent branches from a parallel gateway after the shared activity, rather than sequencing them.

**LRN-087** (T5; refines ACT-03; 1 description(s); confirmed: no)  
When the description explicitly says that an information system provides information or performs a check: Model each such automated behavior as a service task at the point in the described sequence where it occurs.

**LRN-088** (T5; new; 1 description(s); confirmed: yes)  
When the description requires every activity in a set to be completed but does not prescribe their order: Model the activities as parallel branches and synchronize them before any activity that depends on completion of the entire set.

**LRN-089** (T6; refines FID-02; 1 description(s); confirmed: no)  
When the description states that an item is submitted and separately registered before it is handled by another participant: Model submission and registration as distinct activities, in the stated order, before the subsequent handling activity.

**LRN-091** (T5; refines ACT-04; 1 description(s); confirmed: no)  
When the description states that one participant sends information to another as a distinct step before the recipient handles it: Model the sending as a send task in the sender’s process and represent the communication to the recipient with a message flow.

**LRN-092** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that an actor performs a subsequent action according to the result of an earlier assessment: Model the subsequent action as a separate BPMN activity after the assessment, preserving the stated dependency and outcomes.

**LRN-093** (T5; refines EVT-02; 1 description(s); confirmed: yes)  
When the description presents successive activities and gives no further step after the last one: Connect the activities with sequence flows in the described order, and connect the final activity to an end event.

**LRN-094** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description lists multiple alternative methods for performing one activity: Model each stated method on a separate branch of an exclusive split, then merge the alternatives before the shared continuation; do not omit any stated method.

## Example-specific guidelines
