import React from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import Underline from '@tiptap/extension-underline';
import Link from '@tiptap/extension-link';
import { 
  Bold, 
  Italic, 
  Underline as UnderlineIcon, 
  List, 
  ListOrdered,
  Link as LinkIcon,
  Undo,
  Redo,
  Type,
  Heading1,
  Heading2
} from 'lucide-react';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';

const MenuBar = ({ editor }) => {
  if (!editor) return null;

  const addLink = () => {
    const url = window.prompt('URL odkazu:');
    if (url) {
      editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
    }
  };

  const MenuButton = ({ onClick, isActive, children, title }) => (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={cn(
        "p-2 rounded hover:bg-gray-100 transition-colors",
        isActive && "bg-gray-200 text-slate-900"
      )}
    >
      {children}
    </button>
  );

  return (
    <div className="flex flex-wrap items-center gap-1 p-2 border-b bg-gray-50 rounded-t-lg">
      <MenuButton
        onClick={() => editor.chain().focus().toggleBold().run()}
        isActive={editor.isActive('bold')}
        title="Tučné"
      >
        <Bold className="w-4 h-4" />
      </MenuButton>
      
      <MenuButton
        onClick={() => editor.chain().focus().toggleItalic().run()}
        isActive={editor.isActive('italic')}
        title="Kurzíva"
      >
        <Italic className="w-4 h-4" />
      </MenuButton>
      
      <MenuButton
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        isActive={editor.isActive('underline')}
        title="Podtržené"
      >
        <UnderlineIcon className="w-4 h-4" />
      </MenuButton>
      
      <div className="w-px h-6 bg-gray-300 mx-1" />
      
      <MenuButton
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        isActive={editor.isActive('heading', { level: 1 })}
        title="Nadpis 1"
      >
        <Heading1 className="w-4 h-4" />
      </MenuButton>
      
      <MenuButton
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        isActive={editor.isActive('heading', { level: 2 })}
        title="Nadpis 2"
      >
        <Heading2 className="w-4 h-4" />
      </MenuButton>
      
      <MenuButton
        onClick={() => editor.chain().focus().setParagraph().run()}
        isActive={editor.isActive('paragraph')}
        title="Odstavec"
      >
        <Type className="w-4 h-4" />
      </MenuButton>
      
      <div className="w-px h-6 bg-gray-300 mx-1" />
      
      <MenuButton
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        isActive={editor.isActive('bulletList')}
        title="Odrážky"
      >
        <List className="w-4 h-4" />
      </MenuButton>
      
      <MenuButton
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        isActive={editor.isActive('orderedList')}
        title="Číslovaný seznam"
      >
        <ListOrdered className="w-4 h-4" />
      </MenuButton>
      
      <div className="w-px h-6 bg-gray-300 mx-1" />
      
      <MenuButton
        onClick={addLink}
        isActive={editor.isActive('link')}
        title="Odkaz"
      >
        <LinkIcon className="w-4 h-4" />
      </MenuButton>
      
      <div className="w-px h-6 bg-gray-300 mx-1" />
      
      <MenuButton
        onClick={() => editor.chain().focus().undo().run()}
        isActive={false}
        title="Zpět"
      >
        <Undo className="w-4 h-4" />
      </MenuButton>
      
      <MenuButton
        onClick={() => editor.chain().focus().redo().run()}
        isActive={false}
        title="Vpřed"
      >
        <Redo className="w-4 h-4" />
      </MenuButton>
    </div>
  );
};

export const RichTextEditor = ({ 
  content, 
  onChange, 
  placeholder = "Začněte psát...",
  className = ""
}) => {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      Placeholder.configure({
        placeholder,
      }),
      Underline,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'text-blue-600 underline',
        },
      }),
    ],
    content: content || '',
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none focus:outline-none min-h-[200px] p-4',
      },
    },
  });

  // Update editor content when prop changes
  React.useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content || '');
    }
  }, [content, editor]);

  return (
    <div className={cn("border rounded-lg overflow-hidden bg-white", className)}>
      <MenuBar editor={editor} />
      <EditorContent editor={editor} />
    </div>
  );
};

export default RichTextEditor;
