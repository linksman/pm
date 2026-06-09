import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/lib/kanban";
import { vi, beforeEach, afterEach } from "vitest";

const mockOnLogout = vi.fn();

function mockFetch(board = initialData) {
  return vi.spyOn(global, "fetch").mockImplementation((url) => {
    const path = typeof url === "string" ? url : url.toString();
    if (path.includes("/api/board")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(board),
      } as Response);
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
  });
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

async function renderBoard(user = {}) {
  mockFetch();
  render(<KanbanBoard onLogout={mockOnLogout} user={user} />);
  await waitFor(() => screen.getAllByTestId(/column-/i));
}

describe("KanbanBoard", () => {
  it("renders five columns after loading", async () => {
    await renderBoard();
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("shows user name and picture when provided", async () => {
    await renderBoard({ name: "Jane Doe", email: "jane@example.com", picture: null });
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
  });

  it("shows no user info when not provided", async () => {
    await renderBoard();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("renames a column", async () => {
    await renderBoard();
    const column = screen.getAllByTestId(/column-/i)[0];
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    await renderBoard();
    const column = screen.getAllByTestId(/column-/i)[0];
    const addButton = within(column).getByRole("button", { name: /add a card/i });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));
    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", { name: /delete new card/i });
    await userEvent.click(deleteButton);
    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });
});
