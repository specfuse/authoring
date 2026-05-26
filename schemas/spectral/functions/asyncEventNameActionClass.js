"use strict";

// specfuse-async-event-name-action-class
//
// The action verb's suffix on a message's x-label.action determines the
// required payload shape. This rule cross-checks suffix vs payload structure
// after bundling.
//
//   *Created  → payload requires { <id>, after }, MUST NOT include before
//   *Updated  → payload requires { <id>, before, after }
//   *Deleted  → payload requires { <id>, before }, MUST NOT include after
//   anything else (state transition) → payload requires { <id>, before, after };
//                                       optional `context` allowed
//
// Given: $.channels[*].messages[*]

const CUD_SUFFIX_TO_SHAPE = {
  Created: { hasBefore: false, hasAfter: true },
  Updated: { hasBefore: true, hasAfter: true },
  Deleted: { hasBefore: true, hasAfter: false },
};

function payloadProps(message) {
  const payload = message && message.payload;
  if (!payload || typeof payload !== "object") return null;
  const props = payload.properties;
  if (!props || typeof props !== "object") return null;
  return props;
}

module.exports = function asyncEventNameActionClass(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;
  if (targetVal["x-message-category"] !== "event") return;

  const xLabel = targetVal["x-label"];
  if (!xLabel || typeof xLabel !== "object") return;
  const action = xLabel.action;
  if (typeof action !== "string") return;

  const messageName = targetVal.name || "<unnamed>";
  const props = payloadProps(targetVal);
  if (!props) {
    return [
      {
        message: `Message ${messageName} has no payload.properties; cannot validate action-class shape.`,
      },
    ];
  }

  const hasBefore = Object.prototype.hasOwnProperty.call(props, "before");
  const hasAfter = Object.prototype.hasOwnProperty.call(props, "after");

  // Determine action class from suffix
  const cudSuffix = ["Created", "Updated", "Deleted"].find((s) => action.endsWith(s));
  const expected = cudSuffix ? CUD_SUFFIX_TO_SHAPE[cudSuffix] : { hasBefore: true, hasAfter: true };

  const issues = [];
  if (expected.hasBefore && !hasBefore) {
    issues.push(`expected payload.properties.before but it is missing`);
  }
  if (!expected.hasBefore && hasBefore) {
    issues.push(`payload.properties.before is forbidden for *${cudSuffix} events`);
  }
  if (expected.hasAfter && !hasAfter) {
    issues.push(`expected payload.properties.after but it is missing`);
  }
  if (!expected.hasAfter && hasAfter) {
    issues.push(`payload.properties.after is forbidden for *${cudSuffix} events`);
  }

  if (issues.length === 0) return;

  const className = cudSuffix
    ? `*${cudSuffix} (action class: ${cudSuffix.toLowerCase()})`
    : `state transition (suffix '${action}')`;
  return [
    {
      message: `Message ${messageName} payload-shape mismatch for ${className}: ${issues.join("; ")}.`,
    },
  ];
};
