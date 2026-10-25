# Good and Bad Tests

## Good Tests

**Integration-style**: Test through real interfaces, not mocks of internal parts.

```typescript
// GOOD: Tests observable behavior
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});
```

Characteristics:

- Tests behavior users/callers care about
- Uses public API only
- Survives internal refactors
- Describes WHAT, not HOW
- One logical assertion per test

## Bad Tests

**Implementation-detail tests**: Coupled to internal structure.

```typescript
// BAD: Tests implementation details
test("checkout calls paymentService.process", async () => {
  const mockPayment = jest.mock(paymentService);
  await checkout(cart, payment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});
```

Red flags:

- Mocking internal collaborators
- Testing private methods
- Asserting on call counts/order
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT
- Verifying through external means instead of interface

```typescript
// BAD: Bypasses interface to verify
test("createUser saves to database", async () => {
  await createUser({ name: "Alice" });
  const row = await db.query("SELECT * FROM users WHERE name = ?", ["Alice"]);
  expect(row).toBeDefined();
});

// GOOD: Verifies through interface
test("createUser makes user retrievable", async () => {
  const user = await createUser({ name: "Alice" });
  const retrieved = await getUser(user.id);
  expect(retrieved.name).toBe("Alice");
});
```

## Edge cases to try

Tests on typical inputs say little about the edges. For each input the behavior reads, ask
which of these apply, and write a test for each one that does: zero, one, the minimum, the
maximum, just above and just below a limit, empty, missing, duplicate, negative, too long,
wrong format, a timeout, the first and the last item.

## Pick a technique from the shape of the behavior

| The behavior | Technique | What the tests cover |
|---|---|---|
| Inputs fall into groups that behave the same | Equivalence groups | One value from each valid and each invalid group |
| It changes at a limit, a count or a date | Boundary values | On, just below and just above each limit |
| The result depends on a mix of conditions | Decision table | One test per rule, plus the combinations that should be impossible |
| It depends on what happened before (a status, a lifecycle) | State transitions | Each allowed move, each refused move, a repeated event, a restart |
| A rule must hold for any input (a round trip, an order kept) | Property test | The rule checked over many generated inputs |
| The right answer is hard to know, but how two answers relate is known | Metamorphic test | Change the input in a known way, check the output changes the same way |
