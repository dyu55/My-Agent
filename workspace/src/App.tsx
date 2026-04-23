import React, { useState } from 'react';
import TodoList from './components/TodoList';
import { TodoProvider, useTodoContext } from './context/TodoContext';
import './App.css';

function AddTodoForm() {
  const [text, setText] = useState('');
  const { addTodo } = useTodoContext();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim()) {
      addTodo(text);
      setText('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 mb-4">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="添加新任务..."
        className="flex-1 px-3 py-2 border rounded"
      />
      <button type="submit" className="px-4 py-2 bg-blue-500 text-white rounded">
        添加
      </button>
    </form>
  );
}

function App() {
  return (
    <TodoProvider>
      <div className="app-container">
        <h1>React Todo List</h1>
        <AddTodoForm />
        <TodoList />
      </div>
    </TodoProvider>
  );
}

export default App;
