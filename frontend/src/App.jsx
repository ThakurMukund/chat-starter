import React, { useEffect, useState, useRef } from 'react'


export default function App() {
    const [connected, setConnected] = useState(false)
    const [messages, setMessages] = useState([])
    const wsRef = useRef(null)
    const clientId = 'client-' + Math.floor(Math.random() * 10000)


    useEffect(() => {
        const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}`)
        wsRef.current = ws
        ws.onopen = () => setConnected(true)
        ws.onmessage = (ev) => {
            setMessages(m => [...m, ev.data])
        }
        ws.onclose = () => setConnected(false)
        return () => ws.close()
    }, [])


    const send = () => {
        const input = document.getElementById('msg')
        if (!input.value) return
        wsRef.current.send(input.value)
        setMessages(m => [...m, `you: ${input.value}`])
        input.value = ''
    }


    return (
        <div style={{ padding: 20, fontFamily: 'sans-serif' }}>
            <h2>Chat Starter</h2>
            <div>Status: {connected ? 'connected' : 'disconnected'}</div>
            <div style={{ height: 300, overflow: 'auto', border: '1px solid #ccc', padding: 8, marginTop: 8 }}>
                {messages.map((m, i) => (<div key={i}>{m}</div>))}
            </div>
            <div style={{ marginTop: 8 }}>
                <input id="msg" placeholder="Type..." />
                <button onClick={send}>Send</button>
            </div>
        </div>
    )
}