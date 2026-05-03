import argparse
from app import add_todo, list_todos, complete_todo, delete_todo

def main():
    parser = argparse.ArgumentParser(description='TODO CLI Application')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new TODO')
    add_parser.add_argument('title', help='TODO title')
    add_parser.add_argument('--description', default='', help='TODO description')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all TODOs')
    
    # Complete command
    complete_parser = subparsers.add_parser('complete', help='Mark TODO as completed')
    complete_parser.add_argument('id', type=int, help='TODO ID to complete')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a TODO')
    delete_parser.add_argument('id', type=int, help='TODO ID to delete')
    
    args = parser.parse_args()
    
    if args.command == 'add':
        add_todo(args.title, args.description)
    elif args.command == 'list':
        list_todos()
    elif args.command == 'complete':
        complete_todo(args.id)
    elif args.command == 'delete':
        delete_todo(args.id)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()