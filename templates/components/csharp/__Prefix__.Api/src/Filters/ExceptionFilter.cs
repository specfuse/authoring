// Seeded once by `specfuse authoring add-component`. Yours to change.
using {{Prefix}}.Domain.Exceptions;
using {{Prefix}}.Domain.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;

namespace {{Prefix}}.Api.Filters;

/// <summary>
/// Turns the generated domain exceptions into HTTP responses carrying their
/// <see cref="Error"/> list. Anything else becomes a 500 that leaks no detail.
/// Extend it for exceptions of your own.
/// </summary>
public sealed class ExceptionFilter(ILogger<ExceptionFilter> logger) : IExceptionFilter
{
    public void OnException(ExceptionContext context)
    {
        (int status, List<Error>? errors) = context.Exception switch
        {
            BadRequestException e => (BadRequestException.StatusCode, e.Errors),
            UnauthorizedException e => (UnauthorizedException.StatusCode, e.Errors),
            ForbiddenException e => (ForbiddenException.StatusCode, e.Errors),
            NotFoundException e => (NotFoundException.StatusCode, e.Errors),
            ConflictException e => (ConflictException.StatusCode, e.Errors),
            PreconditionFailedException e => (PreconditionFailedException.StatusCode, e.Errors),
            UnprocessableEntityException e => (UnprocessableEntityException.StatusCode, e.Errors),
            _ => (InternalException.StatusCode, null),
        };

        if (errors is null)
            logger.LogError(context.Exception, "Unhandled exception");

        context.Result = new ObjectResult(errors ?? new InternalException(InternalException.ErrorMessage).Errors)
        {
            StatusCode = status,
        };
        context.ExceptionHandled = true;
    }
}
