# Execution Control

A developer console for inspecting a coding agent's persisted work.

- Deep blue-black surfaces, cyan execution signals, amber context labels, straight panel edges, and a fine technical grid.
- Monospace interface labels and code; compact sans-serif task and result text.
- A command strip and workspace explorer surround the active mission. Results form a compact telemetry strip instead of large dashboard cards.
- The execution board draws arrows from the actual `depends_on` relationships. Branches are retained; adjacent independent steps are not connected. The graph redraws when the viewport or selected run changes.
- Outcome and latest tool output sit side by side. Separate tabs expose line-numbered diffs and expandable persisted events.
- On mobile, the explorer becomes a horizontal run selector, dependencies flow vertically, and the output panels stack. Code scrolls inside its own pane.
- Status text accompanies color. Skip navigation, visible keyboard focus, labelled regions, and native buttons remain available.

The viewer remains read-only. Metrics, graph nodes, terminal output, and file changes come from real persisted run data. The screenshot task uses a labelled deterministic model replay with real tool execution and ten passing tests.
