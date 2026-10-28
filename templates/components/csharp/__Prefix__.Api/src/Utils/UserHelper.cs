// Seeded once by `specfuse authoring add-component`. Yours to change.
//
// Generated controllers call UserHelper.GetUser(User) to build the CallerContext
// they pass to the domain. The generator only references it by name, so this
// class is hand-written: map your identity provider's claims here (user id,
// roles, tenant memberships) once authentication is wired in.
using System.Security.Claims;
using {{Prefix}}.Domain.Users;

namespace {{Prefix}}.Api.Utils;

public static class UserHelper
{
    public static AuthenticatedUser GetUser(ClaimsPrincipal user) =>
        new(user.FindFirst(ClaimTypes.NameIdentifier)?.Value ?? user.Identity?.Name ?? "anonymous");
}
