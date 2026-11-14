# DeepSeek Harness Creator Mode - Usage Examples

## What is Creator Mode?

Creator Mode in DeepSeek Harness is a powerful workspace for building and customizing DSH itself. It provides access to:

1. **Plugin Management** - Create, enable, disable, and manage plugins
2. **Cordis Inspect Tools** - Query services, events, configs, and tools
3. **Agent Tools** - Manage subagents, workflows, and task delegation
4. **File Operations** - Read, write, and edit files
5. **Web Integration** - Search and fetch web content

## Example 1: Plugin Management

### Listing Plugins
```javascript
plugin_manager({ action: "list_plugins" })
```

### Listing Bundles
```javascript
plugin_manager({ action: "list_bundles" })
```

### Installing a Bundle
```javascript
plugin_manager({
  action: "install_bundle",
  target: "@deepseek-ai/dsh-bundle-name@version"
})
```

## Example 2: Cordis Inspect System

### Listing All Providers
```javascript
cordis_inspect_list()
```

### Querying Tools
```javascript
cordis_inspect_query({
  platform: "host",
  provider: "Tool",
  method: "listTools"
})
```

## Example 3: Agent Delegation

### Creating a Subagent
```javascript
subagent({
  description: "Task description",
  prompt: "Complete task instructions"
})
```

### Running a Workflow
```javascript
workflow({
  script: `
    // JavaScript workflow script
    const results = await pipeline(items, stages);
    return results;
  `,
  meta: {
    name: "workflow-name",
    description: "What this workflow does"
  }
})
```

## Example 4: File Operations

### Reading Files
```javascript
read({ file_path: "path/to/file.txt" })
```

### Writing Files
```javascript
write({
  file_path: "path/to/file.txt",
  content: "File content here"
})
```

### Editing Files
```javascript
edit({
  file_path: "path/to/file.txt",
  old_string: "Text to replace",
  new_string: "Replacement text"
})
```

## Example 5: Task and Goal Management

### Creating Goals
```javascript
create_goal({
  objective: "What needs to be accomplished",
  max_goal_rounds: 10
})
```

### Managing Tasks
```javascript
todo_write({
  todos: [
    { content: "Task 1", status: "pending" },
    { content: "Task 2", status: "in_progress" }
  ]
})
```

## Best Practices

1. **Always use cordis_inspect_list** before writing plugin code to understand available services
2. **Use subagents** for independent, self-contained tasks
3. **Use workflows** for complex, multi-agent orchestration
4. **Leverage skills** for specialized tasks (Office, file operations, etc.)
5. **Ask questions** when you need confirmation or missing information

## Key Tools in Creator Mode

- **plugin_manager** - Manage plugins and bundles
- **cordis_inspect_list/query** - Explore the system architecture
- **subagent/subagent_fork** - Delegate independent tasks
- **workflow** - Orchestrate multi-agent workflows
- **create_goal/update_goal** - Define and track objectives
- **schedule_create/list/view/edit** - Manage scheduled tasks
- **read/write/edit** - File operations with safety checks

---

This example file demonstrates the core concepts of Creator Mode in DeepSeek Harness. Use it as a reference when building custom plugins, workflows, or automation systems.
