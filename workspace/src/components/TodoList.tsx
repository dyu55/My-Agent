import React, { useContext } from 'react';
import { TodoContext, useTodoContext } from '../context/TodoContext';

const TodoList: React.FC = () => {
  const { todos, filter, setFilter, deleteTodo, toggleTodo } = useTodoContext();

  const filteredTodos = todos.filter(todo => {
    if (filter === 'completed') return todo.completed;
    if (filter === 'uncompleted') return !todo.completed;
    return true;
  });

  return (
    <div className="p-6 bg-white shadow-xl rounded-lg max-w-xl mx-auto">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">我的待办事项</h2>

      {/* 筛选按钮 */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1 rounded ${filter === 'all' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
        >
          全部
        </button>
        <button
          onClick={() => setFilter('completed')}
          className={`px-3 py-1 rounded ${filter === 'completed' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
        >
          已完成
        </button>
        <button
          onClick={() => setFilter('uncompleted')}
          className={`px-3 py-1 rounded ${filter === 'uncompleted' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
        >
          未完成
        </button>
      </div>

      {/* 任务列表 */}
      <ul className="space-y-2">
        {filteredTodos.map(todo => (
          <li key={todo.id} className="flex items-center gap-2 p-2 border rounded">
            <input
              type="checkbox"
              checked={todo.completed}
              onChange={() => toggleTodo(todo.id)}
            />
            <span style={{ textDecoration: todo.completed ? 'line-through' : 'none' }}>
              {todo.text}
            </span>
            <button
              onClick={() => deleteTodo(todo.id)}
              className="ml-auto text-red-500 hover:text-red-700"
            >
              删除
            </button>
          </li>
        ))}
      </ul>

      {filteredTodos.length === 0 && (
        <p className="text-gray-500 text-center py-4">
          {todos.length === 0 ? '暂无待办事项' : '没有符合条件的任务'}
        </p>
      )}
    </div>
  );
};

export default TodoList;
