# Activity Diagram - F1: Sign up, log in, log out

Routes: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout` (`auth_routes.py`, `UserService.register` / `login`, `TokenService.revoke`).

No page of the application can be used anonymously: every route except `register` and `login` requires a valid JWT.

```mermaid
flowchart TD
    Start([Visitor arrives on the application]) --> HasAccount{Already has an account?}

    %% ===== Sign up =====
    HasAccount -- No --> EnterInfo[Enter username, email, password]
    EnterInfo --> FormatOk{"Format valid?<br/>username 3-30 chars<br/>valid email<br/>password 8-72 chars, max 72 bytes"}
    FormatOk -- No --> ShowFieldError[Show the error under the field<br/>frontend check, else 422] --> EnterInfo
    FormatOk -- Yes --> UsernameFree{Username free?}
    UsernameFree -- No --> UsernameTaken[409: Username already used] --> EnterInfo
    UsernameFree -- Yes --> EmailFree{Email free?}
    EmailFree -- No --> EmailTaken[409: Email already used] --> EnterInfo
    EmailFree -- Yes --> CreateAccount[Hash the password with bcrypt<br/>and create the account]
    CreateAccount --> AutoLogin[Log in automatically<br/>with the same credentials]
    AutoLogin --> CheckCredentials

    %% ===== Log in =====
    HasAccount -- Yes --> EnterCredentials[Enter username and password]
    EnterCredentials --> CheckCredentials{Username exists and<br/>password correct?}
    CheckCredentials -- No --> BadCredentials[401: Incorrect username or password] --> EnterCredentials
    CheckCredentials -- Yes --> Banned{Account banned?}
    Banned -- Yes --> ShowBanned[403: This account has been banned] --> EndRefused([Access refused])
    Banned -- No --> Suspended{Suspension still running?}
    Suspended -- Yes --> ShowSuspended[403: This account is suspended until date] --> EndRefused
    Suspended -- No --> IssueToken[Issue a JWT<br/>stored by the frontend]
    IssueToken --> Access([Access to the application])

    %% ===== Log out =====
    Access --> LogOut[Log out]
    LogOut --> Revoke[Store the SHA-256 hash of the token<br/>in revoked_tokens until it expires]
    Revoke --> EndOut([Back to the login page])
```

While the user is logged in, every request goes through `deps.get_user()`. It rejects (403) a revoked or invalid token, a deleted account, and an account banned or suspended after the token was issued. The frontend then sends the user back to the login page.
