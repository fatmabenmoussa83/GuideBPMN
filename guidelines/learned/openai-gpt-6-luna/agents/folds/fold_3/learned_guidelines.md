# Learned guidelines: GPT-6 Luna, Reuse training, round 3 (44 descriptions)

86 generic and 4 example-specific error-driven guidelines; 38 generic guidelines confirmed. Full records (evidence, confirmation tests, provenance): `learned_guidelines.json`.

## Generic guidelines

**LRN-039** (T6; refines FID-03; 19 description(s); confirmed: yes)  
When the description distinguishes activities or outcomes by their action, object, recipient, or stage: Use BPMN labels that preserve those stated distinctions rather than substituting a different action or outcome.

**LRN-002** (T6; refines FID-03; 14 description(s); confirmed: yes)  
When the description identifies actions or outcomes at distinct stages of a process: Label each BPMN element to reflect the action or outcome described at that stage; do not substitute a different action, a later-stage action, or an unsupported outcome.

**LRN-016** (T5; refines GW-04; 9 description(s); confirmed: yes)  
When the description states that multiple follow-up activities after the same point must all occur, without describing them as alternatives: Model the activities as concurrent branches using a parallel gateway, and synchronize them with a parallel gateway before any subsequent activity that depends on all branches being complete.

**LRN-013** (T6; refines FID-03; 8 description(s); confirmed: yes)  
When the description explicitly states an activity’s action, object, recipient, or multiple coordinated actions: Preserve those stated details in the BPMN task label rather than omitting or substituting them.

**LRN-026** (T5; refines PROC-03; 8 description(s); confirmed: yes)  
When the description identifies a decision, conditional action, or stopping outcome between activities: Model every stated transition with sequence flows, including flows into and out of gateways, and connect each outcome to its next step or end.

**LRN-010** (T5; refines FLOW-01; 6 description(s); confirmed: yes)  
When the description presents process activities in a stated order: Model the corresponding flow nodes in that order with sequence flows, connecting the start event to the initial activity and the final activity to the end event.

**LRN-021** (T6; refines FID-03; 6 description(s); confirmed: yes)  
When the description states an activity or outcome whose surrounding context is already clear from the process flow: Use a concise BPMN label that preserves the activity or outcome, without adding explanatory context that does not distinguish it from other elements.

**LRN-004** (T5; refines FID-02; 5 description(s); confirmed: yes)  
When the description lists multiple actions in an order and does not indicate that they occur concurrently or independently: Model the actions in the stated order using sequence flows; do not use parallel branches unless the description supports concurrent or independent execution.

**LRN-031** (T5; refines ACT-07; 5 description(s); confirmed: yes)  
When the description states that a distinct activity is performed while other activities are in progress and that a later activity depends on their completion: Model the distinct activity and the other required work on concurrent branches, then synchronize those branches before the dependent activity.

**LRN-008** (T5; refines GW-04; 4 description(s); confirmed: no)  
When the description identifies multiple independent activities that must all be completed before a later activity can begin: model the activities as parallel branches and synchronize them with a parallel join before the later activity

**LRN-017** (T5; refines GW-01; 4 description(s); confirmed: yes)  
When the description lists mutually exclusive ways to achieve an outcome: Model each stated alternative as a distinct activity on an exclusive-gateway branch, rather than combining the alternatives into one generic activity.

**LRN-018** (T6; refines EVT-01; 4 description(s); confirmed: yes)  
When the description says a participant performs a concrete action that initiates the process, rather than merely identifying an event that triggers it: Model the initiating action as a task after the start event and before the subsequent activity; do not represent the action only as a start event.

**LRN-063** (T6; refines FID-03; 4 description(s); confirmed: yes)  
When the description states the meaning of an activity, event, or gateway: label that BPMN element to preserve its stated meaning rather than substituting a generic or inferred alternative

**LRN-005** (T6; refines FID-01; 2 description(s); confirmed: no)  
When the description names alternative actions that can each signal or cause the same subsequent step: model each stated alternative as a distinct activity or event and preserve its path to the shared step, rather than omitting an alternative or substituting a different action

**LRN-007** (T6; refines EVT-02; 2 description(s); confirmed: no)  
When the description states that work is performed as the process concludes: Model that work as an activity before the end event; use the end event only to mark process termination.

**LRN-009** (T5; refines FID-01; 2 description(s); confirmed: yes)  
When the description says an activity may occur in addition to the main sequence: Model the activity on an optional path, using a decision gateway to determine whether it occurs, and rejoin the main sequence afterward.

**LRN-014** (T5; refines FID-01; 2 description(s); confirmed: yes)  
When the description states that a participant selects or specifies inputs before a subsequent process action: Model that selection or specification as an explicit task before the dependent action.

**LRN-020** (T5; refines FID-02; 2 description(s); confirmed: yes)  
When the description names multiple distinct activities together in one sentence or clause, including as a coordinated list: Represent each distinct activity as its own BPMN task, and preserve only the ordering or dependencies that the description states.

**LRN-023** (T5; refines ACT-07; 2 description(s); confirmed: no)  
When the description states that feedback may lead to repeating an earlier activity: Model the repetition as a loop with a decision gateway and a flow returning to the appropriate activity.

**LRN-025** (T5; refines FID-01; 2 description(s); confirmed: yes)  
When the description states that review results can lead to feedback and a need to repeat an earlier review before proceeding: Model providing feedback as an explicit activity, then use a decision gateway to route the repeat-review path back to the relevant review and the continuation path onward.

**LRN-027** (T6; refines FID-03; 2 description(s); confirmed: no)  
When the description explicitly states an action performed by a participant, and a related receipt or outcome could be mistaken for that action: Label the BPMN activity with the stated action and preserve its direction; do not replace it with the corresponding action from another participant’s perspective.

**LRN-032** (T6; new; 2 description(s); confirmed: no)  
When the description explicitly identifies who performs an activity: Use a concise BPMN activity label that preserves the stated performer as well as the action, when needed to distinguish whose action it is.

**LRN-037** (T7; refines COL-03; 2 description(s); confirmed: no)  
When the description identifies an external system or organization as a sender or recipient of information exchanged with the process: model it as a separate participant and represent the described exchanges with message flows between the participants, not solely with events inside one process

**LRN-046** (T6; new; 2 description(s); confirmed: no)  
When the description states a condition that determines which alternative path is taken: Label the corresponding BPMN gateway with that stated condition, rather than with an adjacent activity or a downstream outcome.

**LRN-052** (T5; refines EVT-03; 2 description(s); confirmed: no)  
When the description says that information or a decision is requested from other participants and that the process waits for their responses before continuing: Model the wait after the request as an intermediate message catch event in the sequence flow.

**LRN-057** (T3; refines PROC-05; 2 description(s); confirmed: yes)  
When the description says that a sequence of work must happen before the process proceeds to other described work: Model that sequence as connected to the main process flow, with its completion leading to the subsequent work, rather than as a detached start-to-end chain.

**LRN-059** (T6; refines FID-03; 2 description(s); confirmed: yes)  
When the description states a process trigger that precedes the first activity: Label the start event with the stated trigger, not with the activity that follows it.

**LRN-001** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description states a distinct action that occurs before a later recording or confirmation step: Model that action as its own activity in sequence before the later step; do not use an end event or another outcome element as its substitute.

**LRN-003** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description says that a later activity proceeds only after approval or another decision: Model the described preceding action and approval step in order, then use an exclusive gateway to route the approved path to the dependent activity.

**LRN-006** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description presents successive activities without stating a choice, condition, or decision between them: model the activities in sequence and do not insert an exclusive gateway between them

**LRN-011** (T1; refines XML-06; 1 description(s); confirmed: yes)  
When the description presents activities whose execution order must be represented in BPMN: Represent that order with sequence flows that are direct children of the relevant process or subprocess scope; do not place sequence flows inside activities or other BPMN elements.

**LRN-012** (T5; refines GW-01; 1 description(s); confirmed: no)  
When the description presents alternative ways to initiate a process that lead to the same subsequent handling: Represent the alternatives with an exclusive gateway and converge them before the shared handling; do not invent channel-specific work.

**LRN-015** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a participant supplies multiple distinct categories of information, even when they are mentioned in one combined step: Model each stated information-provision activity explicitly rather than combining distinct categories into a single activity.

**LRN-019** (T6; refines FID-02; 1 description(s); confirmed: yes)  
When the description specifies multiple distinct criteria or dimensions to be evaluated for an item: Model each distinct evaluation as a separate activity rather than combining them into one activity.

**LRN-022** (T6; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a decision is communicated to an affected participant and then describes actions conditional on that decision: Model the communication so it occurs on every outcome path for which it is stated, including paths that skip the conditional action; do not omit an outcome-specific communication when the description requires it.

**LRN-024** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description identifies a concrete activity that initiates the process or an outcome that terminates it: Label the corresponding start or end event with that process boundary condition, rather than with a nearby time reference or an unspecified generic label.

**LRN-028** (T5; refines SUB-05; 1 description(s); confirmed: no)  
When the description states that an action may recur and that each occurrence causes a follow-up action to happen again: Model the recurring action and its follow-up as a loop or cycle so that every occurrence leads to the stated follow-up.

**LRN-029** (T1; refines ACT-05; 1 description(s); confirmed: yes)  
When the description says that a participant performs work by sending information to another participant: Model the sending as a task (use a send task when sending is itself the unit of work). Represent communication separately where appropriate; do not attach a message event definition to a task.

**LRN-030** (T6; refines FID-03; 1 description(s); confirmed: yes)  
When the description distinguishes a participant’s instruction or assignment from the work that another participant is asked to perform: Label the BPMN activity as the instruction or assignment, preserving who directs whom; do not label it as though the directing participant were ordering or performing the requested work.

**LRN-033** (T5; refines GW-06; 1 description(s); confirmed: yes)  
When the description states that one activity is required while an independent activity is performed only when a condition holds: Model the activities as branches of an inclusive gateway, with the required activity on an always-taken branch and the optional activity on a conditional branch; use an inclusive join before any subsequent activity that depends on their completion.

**LRN-034** (T7; refines LANE-01; 1 description(s); confirmed: yes)  
When the description assigns activities to multiple roles or departments within one organization: Represent those responsibilities as lanes within one process, and place each stated activity in the lane of the role or department assigned to it; do not model those internal roles as separate participant pools or connect them with message flows.

**LRN-035** (T7; refines COL-01; 1 description(s); confirmed: yes)  
When the description says that an interaction involves a set of external organizations but does not identify any organization individually: Represent the external participants at the level of identity the description supports; do not invent a specific numbered participant when the organizations are described only as a group.

**LRN-036** (T5; refines EVT-04; 1 description(s); confirmed: no)  
When the description states that a requested communication may be returned without waiting for additional work or only after further work, with a separate notice sent before the eventual response: Model the alternative paths explicitly; on the path with a separate notice, model that communication and then use an intermediate message catch event to wait for the incoming communication before continuing.

**LRN-038** (T5; refines ACT-04; 1 description(s); confirmed: no)  
When the description distinguishes an interim status communication from a separate transmission of information: Model each described communication separately; represent a stated outgoing transmission as a send task rather than treating receipt of an interim status message as that transmission.

**LRN-040** (T7; refines COL-07; 1 description(s); confirmed: no)  
When the description identifies an internal interface through which staff access or view information, and identifies another participant as the party exchanging that information with the process: Model the staff-facing interaction within the organization’s process; do not model the interface as a separate communicating participant unless it is explicitly described as an independent participant.

**LRN-041** (T7; refines COL-04; 1 description(s); confirmed: yes)  
When the description describes communication or a signal between participants, while the underlying work or the receipt of that communication is already represented by activities or events: model the communication with a message flow between the appropriate existing sender and receiver nodes; do not add separate send or receive tasks solely to represent the exchange, or create message flows for physical movement that is not described as communication

**LRN-042** (T5; refines ACT-05; 1 description(s); confirmed: no)  
When the description says that one participant physically hands an item to another participant: Model the recipient's act of taking the item as an activity, rather than as an intermediate catch event.

**LRN-043** (T5; refines FLOW-07; 1 description(s); confirmed: yes)  
When the description states an ongoing obligation and separately states that a later outcome can end or alter it: Model the obligation as recurring from the point it applies, and model the later outcome as changing or stopping future repetitions rather than gating whether the obligation is performed at all.

**LRN-044** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description assigns distinct actions to different parties at the same stage of a process: Model each stated party action as a separate BPMN activity and assign it to the responsible participant or lane.

**LRN-045** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that two participants each perform an action toward the other: model a distinct activity for each stated direction

**LRN-047** (T5; refines ACT-01; 1 description(s); confirmed: no)  
When the description states that a real-world activity is carried out over a period before a later decision: Model the activity as a BPMN task; a time event may mark the period’s end but does not replace the activity.

**LRN-048** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description states that multiple instances of an activity for different recipients are to occur in parallel: Model the instances as parallel work, using parallel multi-instance behavior or concurrent branches as appropriate, rather than as mutually exclusive alternatives.

**LRN-049** (T6; refines FID-03; 1 description(s); confirmed: yes)  
When the description specifies a quantity, frequency, or other scope constraint for an activity: Preserve that constraint in the BPMN activity label rather than weakening it to a more general activity.

**LRN-050** (T5; refines FID-02; 1 description(s); confirmed: yes)  
When the description identifies multiple distinct items that must be prepared or verified before a later step: Model each actionable preparation or verification as a separate activity before the dependent activity, preserving stated dependencies.

**LRN-051** (T5; new; 1 description(s); confirmed: no)  
When the description says a resource must be arranged by discussing terms with its provider: Model identifying a suitable option as a distinct activity before discussing terms with the provider, and connect the activities with a sequence flow.

**LRN-053** (T5; refines FLOW-07; 1 description(s); confirmed: no)  
When the description says that an item or value is tried repeatedly until it meets an acceptance condition: Model the repeated attempt with a decision gateway: exit when the condition is met and loop back for another attempt otherwise.

**LRN-054** (T7; refines LANE-01; 1 description(s); confirmed: no)  
When the description assigns input selection or configuration to a human participant and subsequent execution to an automated system: Represent the human and automated responsibilities as distinct lanes within the same process, and place each activity in the lane of the responsible role or system.

**LRN-055** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description says an occurrence may or may not happen and that its occurrence changes what the process does: Represent the possible occurrence with an appropriate BPMN event or decision gateway, and connect the path for handling it with sequence flows.

**LRN-056** (T1; refines QA-01; 1 description(s); confirmed: yes)  
When the description describes a process to be represented in BPMN: Use XML-ID-valid values for BPMN element IDs, and ensure those IDs are unique within the document.

**LRN-058** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description says to order or otherwise obtain a specified item because that same item is unavailable: Model obtaining the specified item; do not substitute a related or alternative item unless the description supports that substitution.

**LRN-060** (T5; new; 1 description(s); confirmed: no)  
When the description states that each of several items is prepared and checked separately, that successful checks allow a collective next step, and that unsuccessful checks require rework: Model the preparation and checks per item with outcome-dependent routing, and make the collective next step depend on all required successful checks.

**LRN-061** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description assigns different actions to distinct ranges or levels of a measured value: Model a decision gateway with conditional outgoing flows that lead to the action for each range or level.

**LRN-062** (T5; refines ACT-05; 1 description(s); confirmed: no)  
When the description says a participant places an order for goods or services, without identifying the act of sending a message as the work: Model the ordering as a user task unless the description explicitly identifies sending a message as the work.

**LRN-064** (T5; new; 1 description(s); confirmed: yes)  
When the description says that a returned result is refined repeatedly and the changes are sent back to the activity that produced it: Model a connected repetition loop: flow from receiving the result through assessment and refinement to sending the changes back to the producing activity, with the next returned result entering that cycle.

**LRN-065** (T5; refines GW-02; 1 description(s); confirmed: no)  
When the description distinguishes whether required resources are already available from the alternative ways of obtaining any that are unavailable: Model the availability assessment first; route unmet needs to a separate exclusive gateway that selects among the described acquisition alternatives.

**LRN-066** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description identifies multiple distinct items as handled together in one stated action: Model each explicitly distinct item as its own activity, and use a parallel gateway to synchronize those activities before later work only when the description establishes that they occur together or are all required.

**LRN-067** (T6; new; 1 description(s); confirmed: no)  
When the description says that work resumes or continues after an interruption or restart: model the resumed work as an activity in the existing process flow, rather than as a start event representing that work

**LRN-068** (T5; new; 1 description(s); confirmed: no)  
When the description says that required information must be entered before a process phase can begin: Model the information-entry activities before the activities of that phase and connect them to the main flow with sequence flows.

**LRN-069** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description identifies the inputs or actions after which a process can begin: Model the stated prerequisites and begin the subsequent work after them; do not insert earlier setup activities or prerequisite flows unless the description supports them.

**LRN-070** (T5; refines GW-06; 1 description(s); confirmed: no)  
When the description says that an evaluation determines whether a follow-up activity is performed or omitted: Model the choice with an exclusive gateway and conditional paths for performing or skipping the follow-up activity; rejoin the paths before a subsequent activity only when the description states that one follows both outcomes.

**LRN-071** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description says a participant records information about a real-world situation or its outcome: Model the information-recording work as an activity; do not substitute the underlying physical-world activity for it.

**LRN-072** (T3; refines FID-02; 1 description(s); confirmed: no)  
When the description states that an action becomes available only after a milestone in an ongoing process: Model the action in the existing process flow, connected to the relevant milestone by sequence flow, rather than as an independent start event.

**LRN-073** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description says a later action must wait until a condition is met, while the process may continue waiting or providing updates before that happens: Model the condition with a decision gateway: loop back to the waiting or update activity while it is unmet, and proceed to the later action when it is met. Do not represent the condition becoming true as a separate start event or as an activity in place of the decision.

**LRN-074** (T6; refines FID-03; 1 description(s); confirmed: no)  
When the description presents two or more distinct decisions, each with its own alternatives: Label each gateway and its related activities to reflect the specific decision or option they represent; do not transfer labels between decisions.

**LRN-075** (T5; refines EVT-03; 1 description(s); confirmed: yes)  
When the description states that an activity recurs at a fixed time interval: Model the elapsed interval with a timer intermediate catch event in the flow, and connect it to the recurring activity as required by the described repetition.

**LRN-076** (T3; refines PROC-03; 1 description(s); confirmed: no)  
When the description presents a process initiation followed by work in the main process flow: Connect the start event by sequence flow to the first activity in that flow; do not leave it in a separate start-to-end chain.

**LRN-077** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description makes a decision depend on comparing a value derived from other information: Model the necessary calculation or determination as an activity before the decision gateway.

**LRN-078** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that a quantity is measured and the result is used to evaluate a stated criterion: Model the measurement as a distinct activity before the decision that evaluates its result.

**LRN-079** (T5; refines EVT-10; 1 description(s); confirmed: yes)  
When the description states that a participant performs an action that initiates the process: Model the described action as a task in the process flow; do not also represent that same action as a start event.

**LRN-080** (T5; refines ACT-01; 1 description(s); confirmed: no)  
When the description says that an external participant performs a concrete action that initiates the modeled workflow: Model the stated action as a task; use a start event to mark the workflow’s start rather than substituting a start event or a message-sending task for the action.

**LRN-081** (T5; refines FID-01; 1 description(s); confirmed: no)  
When the description states that an item is registered before another participant receives or acts on it: Model the registration as a distinct activity before the subsequent receipt or action.

**LRN-082** (T5; refines EVT-06; 1 description(s); confirmed: no)  
When the description begins with a process activity and states no separate initiating event or trigger: Model a none start event and connect it by sequence flow to the first activity.

**LRN-083** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description states that exactly one of several alternative actions may occur: Model an exclusive gateway before the alternative actions to route the process to the selected action.

**LRN-084** (T5; refines ACT-07; 1 description(s); confirmed: no)  
When the description states that one of multiple alternative actions is chosen after a shared activity: Model an exclusive gateway after the shared activity and route each outgoing branch to its corresponding alternative.

**LRN-085** (T5; refines FID-02; 1 description(s); confirmed: no)  
When the description states that a participant performs a distinct follow-up action after checking or examining something: Model the follow-up action as a separate BPMN activity after the check.

**LRN-086** (T5; refines GW-03; 1 description(s); confirmed: yes)  
When the description says that the normal sequence and one or more retry paths after failed checks lead to the same earlier activity: Model the incoming alternatives through an exclusive merge gateway before that activity, rather than connecting each path directly to it.

## Example-specific guidelines

**EXS-009** (T5; refines ACT-05; 1 description(s); confirmed: no)  
When the description says a requested outcome may be delayed, a separate notice is sent before the outcome, and the process informs a user about that notice: Model receipt of the delay notice as a message event and the user notification as a distinct activity; then model waiting for the requested outcome with an intermediate message catch event.

**EXS-012** (T5; refines FID-02; 1 description(s); confirmed: yes)  
When the description lists multiple distinct documents or prerequisites that must be provided or checked as part of an application: Model each actionable document-related preparation or verification as a separate activity before the application is assessed, and preserve any dependencies stated in the description.

**EXS-013** (T5; refines FID-01; 1 description(s); confirmed: yes)  
When the description gives eligibility or document conditions and institutional context but does not specify how the procedure is carried out, how responses are handled, or what outcomes follow: Model only the activities, decisions, and results stated in the description; do not add application steps, response waits, or outcomes.

**EXS-017** (T5; refines FID-02; 1 description(s); confirmed: yes)  
When the description says that one provider supplies several distinct categories of information as part of one response: Represent each stated category as a distinct activity, and use a parallel gateway to synchronize those activities before subsequent work only when the description establishes that they are provided together or all are needed.
