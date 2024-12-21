import { ForwardedRef, useEffect, useRef, useState } from "react";

interface MessageEntity {
  role: string;
  type: string;
  content: string;
}

function Message({ role, type, content, ref }: MessageEntity & { ref: ForwardedRef<HTMLDivElement> }) {
  let element;
  switch (type) {
    case "text":
    case "error":
      element = <p style={{ whiteSpace: 'pre-wrap' }}>{content}</p>;
      break;
    case "image":
      element = <img src={`data:image/png;base64,${content}`} />;
      break;
  }

  const backgroundColor = role === 'user' ? 'blue' : 'transparent';
  return (
    <div ref={ref} style={{ border: '1px solid gray', padding: 20, backgroundColor }}>
      {element}
    </div>
  );
}

function App() {
  const [messages, setMessages] = useState<MessageEntity[]>([]);
  const [connectionStatus, setConnectionStatus] = useState("Disconnected");
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const firstSegment = window.location.pathname.split('/').filter(Boolean)[0];

    if (!firstSegment) {
      console.log("no session id");
      return;
    }

    // Create a WebSocket connection
    const socket = new WebSocket(`ws://${window.location.hostname}:8001/${firstSegment}`);

    socketRef.current = socket;

    socket.onopen = () => {
      setConnectionStatus("Connected");
      console.log("WebSocket connected");
    };

    socket.onmessage = (event) => {
      console.log("Message received:", event.data);
      const parsed = JSON.parse(event.data);
      console.log("Message parsed:", parsed);

      if (Array.isArray(parsed)) {
        setMessages([...parsed]);
      } else {
        setMessages((prevMessages) => [...prevMessages, parsed]);
      }
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      setConnectionStatus("Error");
    };

    socket.onclose = () => {
      console.log("WebSocket disconnected");
      setConnectionStatus("Disconnected");
    };

    // Cleanup on component unmount
    return () => {
      socket.close();
    };
  }, []);

  const messagesEndRef = useRef<null | HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages]);

  useEffect(() => {
    const interval = setInterval(() => {
      window.location.reload();
    }, 10000); // 10 seconds

    // Cleanup the interval on component unmount
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <p>WebSocket Status: {connectionStatus}</p>
      {messages.map((message, index) => (
        <Message key={index} {...message} ref={index === messages.length - 1 ? messagesEndRef : null} />
      ))}
    </div>
  );
}

export default App
