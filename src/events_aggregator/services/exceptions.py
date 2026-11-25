class DomainError(Exception):
    pass


class EventNotFound(DomainError):
    pass


class EventUnexpectedStatus(DomainError):
    pass


class RegistrationDeadlinePassed(DomainError):
    pass


class SeatUnavailable(DomainError):
    pass


class TicketNotFound(DomainError):
    pass


class SyncAlreadyRunning(DomainError):
    pass


class DuplicateRegistration(DomainError):
    pass
