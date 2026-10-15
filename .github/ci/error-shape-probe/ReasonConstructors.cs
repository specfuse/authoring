// compatibility.md §54, §55. From generator 0.18.0 the six exceptions a
// business rule can refuse with take (string reason, string message) when the
// spec's Error declares `reason`, as the kit's does. Calling each one here
// makes a pin bump that drops a constructor, or a kit Error that stops
// declaring `reason`, fail this build instead of a project's.
using HelloOrders.Domain.Exceptions;

namespace ErrorShapeProbe;

internal static class ReasonConstructors
{
    internal static IEnumerable<Exception> All() =>
    [
        new BadRequestException("invalid_filter", "The filter is malformed."),
        new ForbiddenException("tenant_mismatch", "The order belongs to another tenant."),
        new NotFoundException("not_found", "No order has this id."),
        new ConflictException("template_in_use", "The template is used by an open order."),
        new PreconditionFailedException("precondition_failed", "The order changed since it was read."),
        new UnprocessableEntityException("order_closed", "A closed order takes no new lines."),
    ];
}
