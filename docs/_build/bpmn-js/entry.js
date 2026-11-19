/* bpmn-js Modeler with the "create / append anything" menu (the "..." palette entry of demo.bpmn.io). */
import Modeler from 'bpmn-js/lib/Modeler';
import { CreateAppendAnythingModule } from 'bpmn-js-create-append-anything';

export default class BpmnJS extends Modeler {}
BpmnJS.prototype._modules = [].concat(Modeler.prototype._modules, [CreateAppendAnythingModule]);
