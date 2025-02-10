"use client";
import { useState } from "react";
import { signIn } from "@aws-amplify/auth";

export default function Login() {
  const [formData, setFormData] = useState({ username: "", password: "" });
  const [message, setMessage] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const user = await signIn({
        username: formData.username,
        password: formData.password
      });

      setMessage(`Login successful!`);
    } catch (error: any) {
      setMessage("Error: " + error.message);
    }
  };

  return (
    <div className="flex flex-col items-center p-6 min-h-screen bg-gray-900 text-white">
      <h2 className="text-3xl font-bold mb-4">Login</h2>
      <form onSubmit={handleSubmit} className="flex flex-col space-y-4 w-96 bg-gray-800 p-6 rounded-lg shadow-lg">
        <input
          type="text"
          name="username"
          placeholder="Username"
          onChange={handleChange}
          required
          className="p-3 border border-gray-600 bg-gray-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-green-400"
        />
        <input
          type="password"
          name="password"
          placeholder="Password"
          onChange={handleChange}
          required
          className="p-3 border border-gray-600 bg-gray-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-green-400"
        />
        <button type="submit" className="bg-green-500 hover:bg-green-600 text-white p-3 rounded-lg font-semibold transition">
          Login
        </button>
      </form>
      {message && <p className="mt-4 text-sm">{message}</p>}
    </div>
  );
}
