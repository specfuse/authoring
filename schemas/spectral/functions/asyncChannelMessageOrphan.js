"use strict";

// asyncapi-channel-message-orphan
//
// For every entry in a channel's `messages` map, at least one operation
// somewhere in the spec must reference that message (by name, on the same
// channel address). Orphan entries are likely stale.
//
// Given: $.channels[*].messages[*]

function isReferencedByOperation(operations, channelAddress, messageName) {
  if (!operations || typeof operations !== "object") return false;
  for (const opKey of Object.keys(operations)) {
    const op = operations[opKey];
    if (!op || typeof op !== "object") continue;
    const opChannel = op.channel;
    const opAddress = opChannel && typeof opChannel === "object" ? opChannel.address : null;
    if (opAddress !== channelAddress) continue;
    const opMessages = op.messages;
    if (!Array.isArray(opMessages)) continue;
    for (const msg of opMessages) {
      if (msg && typeof msg === "object" && msg.name === messageName) {
        return true;
      }
    }
  }
  return false;
}

module.exports = function asyncChannelMessageOrphan(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;
  const name = typeof targetVal.name === "string" ? targetVal.name : null;
  if (!name) return;

  // Path shape: ['channels', channelKey, 'messages', messageKey]
  const path = context && Array.isArray(context.path) ? context.path : [];
  if (path.length < 4) return;
  const channelKey = path[1];
  const doc = context && context.document ? context.document.data : undefined;
  const channel =
    doc && doc.channels && typeof doc.channels === "object" ? doc.channels[channelKey] : null;
  if (!channel) return;
  const channelAddress = typeof channel.address === "string" ? channel.address : null;
  if (!channelAddress) return;

  const operations = doc && doc.operations ? doc.operations : undefined;
  if (isReferencedByOperation(operations, channelAddress, name)) return;

  return [
    {
      message: `Channel ${channelAddress} declares message ${name} but no operation references it.`,
    },
  ];
};
