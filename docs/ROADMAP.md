# Features
- q for quit and other hotkeys
- multiple server connections in tabs
- connect modal for user input to connect with all possible security modes, insecure by default

# Test Backlog
- add an extensive write-value test suite across OPC UA datatypes:
  Boolean, SByte, Byte, Int16, UInt16, Int32, UInt32, Int64, UInt64, Float, Double, String, DateTime, Guid, ByteString, XmlElement, LocalizedText, QualifiedName, NodeId, ExpandedNodeId, arrays of supported scalar types, and null/empty edge cases
- include both success and failure cases for coercion, server rejection, read-back verification, and `BadWriteNotSupported` fallback behavior
