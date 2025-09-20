# Undo/Redo Feature Implementation

## Overview
Implemented comprehensive undo/redo functionality for the SuperTerminal application using Ctrl+Z and Ctrl+Y (or Ctrl+Shift+Z).

## Features

### Keyboard Shortcuts
- **Ctrl+Z** - Undo last operation
- **Ctrl+Y** - Redo last undone operation  
- **Ctrl+Shift+Z** - Alternative redo shortcut

### Context Menu Options
- **Undo** - Available when history allows undoing
- **Redo** - Available when history allows redoing

### Supported Operations
All tree-modifying operations are now tracked in history:

1. **Session Management**
   - Creating new SSH/SFTP sessions
   - Renaming sessions (F2)
   - Deleting sessions

2. **Folder Management**
   - Creating new folders
   - Renaming folders
   - Editing folder properties (color, name)
   - Deleting folders

3. **Copy/Paste Operations**
   - Copying sessions and folders
   - Cutting sessions and folders
   - Pasting sessions and folders
   - Multi-selection copy/cut/paste

4. **Drag & Drop**
   - Moving sessions between folders
   - Reordering items

5. **Group Operations**
   - Multi-selection deletion
   - Multi-selection copy/cut/paste

## Technical Implementation

### History Management
- **History Array**: Stores up to 50 states of the session tree
- **History Index**: Tracks current position in history
- **Deep Copying**: Uses `JSON.parse(JSON.stringify())` for state snapshots
- **Automatic Saving**: History is saved after every tree-modifying operation

### State Tracking
- **Initialization**: History is initialized when the tree is first loaded
- **State Capture**: Every operation that modifies `sessionTree` triggers `saveToHistory()`
- **Memory Management**: History is limited to 50 entries to prevent memory issues

### User Experience
- **Visual Feedback**: Context menu shows/hides Undo/Redo options based on availability
- **Selection Clearing**: Selection is cleared after undo/redo operations
- **Tree Refresh**: Tree is re-rendered after undo/redo operations
- **Persistence**: Changes are automatically saved to disk after undo/redo

## Usage Examples

1. **Basic Undo/Redo**:
   - Create a session → Ctrl+Z (session disappears)
   - Ctrl+Y (session reappears)

2. **Complex Operations**:
   - Create folder → Add session to folder → Rename session
   - Ctrl+Z (session name reverts) → Ctrl+Z (session moves to root) → Ctrl+Z (folder disappears)

3. **Multi-Operation Undo**:
   - Select multiple items → Delete → Ctrl+Z (all items restored)

## Benefits
- **Error Recovery**: Users can easily recover from accidental operations
- **Experiment Freedom**: Users can try different arrangements without fear
- **Professional UX**: Standard undo/redo behavior expected in modern applications
- **Comprehensive Coverage**: All tree operations are undoable
