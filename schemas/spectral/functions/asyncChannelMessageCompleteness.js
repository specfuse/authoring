"use strict";

// asyncapi-channel-message-completeness
//
// For every async operation that references a channel, every message in the
// operation's `messages` array MUST also appear in the target channel's
// `messages` map (by message name). After bundling, the operation's channel
// $ref is inlined — so we cross-check the operation's channel.address against
// the top-level channels map and compare message names.
//
// Given: $.operations[*]

function findChannelByAddress(channels, address) {
  if (!channels || typeof channels !== "object" || !address) return null;
  for (const key of Object.keys(channels)) {
    const channel = channels[key];
    if (channel && channel.address === address) {
      return { key, channel };
    }
  }
  return null;
}

function collectChannelMessageNames(channel) {
  const names = new Set();
  if (!channel || !channel.messages || typeof channel.messages !== "object") {
    return names;
  }
  for (const key of Object.keys(channel.messages)) {
    const msg = channel.messages[key];
    if (msg && typeof msg.name === "string") {
      names.add(msg.name);
    }
  }
  return names;
}

module.exports = function asyncChannelMessageCompleteness(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;
  const operation = targetVal;
  const opMessages = operation.messages;
  if (!Array.isArray(opMessages) || opMessages.length === 0) return;

  const channelRef = operation.channel;
  if (!channelRef || typeof channelRef !== "object") return;
  const address = channelRef.address;
  if (typeof address !== "string") return;

  const doc = context && context.document ? context.document.data : undefined;
  const channels = doc && doc.channels ? doc.channels : undefined;
  const match = findChannelByAddress(channels, address);
  if (!match) return;

  const declared = collectChannelMessageNames(match.channel);
  const operationId =
    Array.isArray(context.path) && context.path.length >= 2 ? context.path[1] : "<unknown>";

  const results = [];
  opMessages.forEach((msg, index) => {
    const name = msg && typeof msg.name === "string" ? msg.name : null;
    if (!name) return;
    if (!declared.has(name)) {
      results.push({
        message: `Message ${name} is referenced by operation ${operationId} but is not declared on channel ${address}'s messages map.`,
        path: [...context.path, "messages", index],
      });
    }
  });
  return results;
};
