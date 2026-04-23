import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

// 定义 TodoItem 的类型
type TodoItem = {
  id: string;
  text: string;
  completed: boolean;
};

// 定义 Context 的类型
interface TodoContextType {
  todos: TodoItem[];
  filter: 'all' | 'completed' | 'uncompleted';
  setFilter: (filter: 'all' | 'completed' | 'uncompleted') => void;
  addTodo: (text: string) => void;
  deleteTodo: (id: string) => void;
  toggleTodo: (id: string) => void;
}

// 创建 Context
const TodoContext = createContext<TodoContextType | undefined>(undefined);

// 初始状态和 localStorage Key
const LOCAL_STORAGE_KEY = 'todo-list-state';

// 自定义 Hook 来使用 Context
export const useTodoContext = () => {
  const context = useContext(TodoContext);
  if (context === undefined) {
    throw new Error('useTodoContext must be used within a TodoProvider');
  }
  return context;
};

// Provider 组件
interface TodoProviderProps {
  children: ReactNode;
}

export const TodoProvider: React.FC<TodoProviderProps> = ({ children }) => {
  // 0. Filter 状态
  const [filter, setFilter] = useState<'all' | 'completed' | 'uncompleted'>('all');

  // 1. 从 localStorage 读取初始状态
  const [todos, setTodos] = useState<TodoItem[]>(() => {
    if (typeof window !== 'undefined') {
      const storedTodos = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (storedTodos) {
        try {
          return JSON.parse(storedTodos) as TodoItem[];
        } catch (e) {
          console.error('Error parsing stored todos:', e);
          return [];
        }
      }
    }
    // 默认初始状态
    return [];
  });

  // 2. useEffect 监听 todos 变化，并同步写入 localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(todos));
    }
  }, [todos]);

  // 3. 状态操作函数
  const addTodo = (text: string): void => {
    if (!text.trim()) return;
    const newTodo: TodoItem = {
      id: Date.now().toString(), // 使用时间戳作为唯一ID
      text: text.trim(),
      completed: false,
    };
    setTodos((prevTodos) => [newTodo, ...prevTodos]);
  };

  const deleteTodo = (id: string): void => {
    setTodos((prevTodos) => prevTodos.filter((todo) => todo.id !== id));
  };

  const toggleTodo = (id: string): void => {
    setTodos((prevTodos) =>
      prevTodos.map((todo) =>
        todo.id === id ? { ...todo, completed: !todo.completed } : todo
      )
    );
  };

  // 4. Context Value
  const contextValue: TodoContextType = {
    todos,
    filter,
    setFilter,
    addTodo,
    deleteTodo,
    toggleTodo,
  };

  return (
    <TodoContext.Provider value={contextValue}>
      {children}
    </TodoContext.Provider>
  );
};

// 导出 Context 和 Hook
export { TodoContext, useTodoContext };
