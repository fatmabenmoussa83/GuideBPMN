# Diagram editor bundle

`docs/assets/vendor/bpmn-js/bpmn-modeler-guidebpmn.min.js` is bpmn-js 18.31.0 with the
"create / append anything" menu (the "..." entry of the palette, as on demo.bpmn.io).
It is built once from `entry.js`; the site needs no build step.

    npm install bpmn-js@18.31.0 bpmn-js-create-append-anything@2.2.0 esbuild@0.24.0
    npx esbuild entry.js --bundle --minify --format=iife --global-name=BpmnJSBundle \
      --footer:js="window.BpmnJS=BpmnJSBundle.default;" --outfile=bpmn-modeler-guidebpmn.min.js

The CSS files next to it come from `bpmn-js/dist/assets`. Licences: bpmn.io licence (bpmn-js;
the bpmn.io logo must stay visible on the canvas) and MIT (create-append-anything).
