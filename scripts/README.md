# TigerGraph Scripts Guide

## 🚀 **Quick Start (Recommended)**

For most cases, just use the smart initialization:

```bash
# Handles existing graphs gracefully - safe to run multiple times
python scripts/smart_tigergraph_init.py
```

## 📋 **Available Scripts**

### **🧠 Smart Scripts (Recommended)**

#### `smart_tigergraph_init.py` ✅
**Use this instead of the old init script!**

- ✅ **Detects existing graphs** - Won't try to recreate what exists
- ✅ **Handles conflicts gracefully** - Skips existing vertices/edges
- ✅ **Safe to run multiple times** - Only does what's needed
- ✅ **Clear status reporting** - Shows what exists vs what was created

```bash
python scripts/smart_tigergraph_init.py
```

#### `start_tigergraph_safe.py` 🔄
**Complete startup automation for TigerGraph Community Edition**

- ✅ **Checks Docker status**
- ✅ **Starts/creates container if needed**
- ✅ **Waits for services to be ready**
- ✅ **Runs smart initialization**
- ✅ **Full automation** - One command startup

```bash
python scripts/start_tigergraph_safe.py
```

### **🔧 Legacy Scripts**

#### `init_tigergraph.py` ⚠️ 
**OLD SCRIPT - Use smart_tigergraph_init.py instead!**

- ❌ **Tries to recreate existing graphs** → Causes conflicts
- ❌ **Fails with "already exists" errors**
- ❌ **Not safe to run multiple times**

#### `setup-tigergraph.sh`
**Container setup script - still needed for first-time setup**

```bash
./scripts/setup-tigergraph.sh
```

## 🎯 **Common Scenarios**

### **Starting Fresh**
```bash
# 1. Setup container (first time only)
./scripts/setup-tigergraph.sh

# 2. Initialize graph (safe to repeat)
python scripts/smart_tigergraph_init.py
```

### **System Already Running**
```bash
# Just run smart init - it'll detect existing setup
python scripts/smart_tigergraph_init.py
```

### **Complete Automated Startup**
```bash
# Handles everything automatically
python scripts/start_tigergraph_safe.py
```

### **Troubleshooting**
```bash
# Check container status
docker ps | grep tigergraph

# Check logs
docker logs tigergraph

# Access GraphStudio manually
# http://localhost:14240
```

## ✅ **Expected Output (Success)**

### When Graph Already Exists:
```
🎉 TigerGraph is already fully initialized and ready!
Graph exists with vertices - no initialization needed
```

### When Creating New Graph:
```
Graph setup completed: New graph created successfully
Schema setup completed: Schema loaded and queries installed successfully
🎉 Smart initialization completed successfully!
```

## ❌ **Old Error (Fixed)**

**Before smart scripts:**
```
❌ The graph name conflicts with another type or existing graph names!
❌ The vertex name Person is used by another object!
```

**After smart scripts:**
```
✅ TigerGraph is already fully initialized and ready!
✅ Graph exists with vertices - no initialization needed
```

## 📊 **Integration with Makefile**

The Makefile has been updated to use smart initialization:

```bash
# Uses smart_tigergraph_init.py automatically
make tigergraph-init
```

## 🎉 **Key Benefits**

1. **No More Conflicts** - Handles existing graphs gracefully
2. **Automation** - Community Edition startup fully automated  
3. **Idempotent** - Safe to run multiple times
4. **Clear Feedback** - Always know what's happening
5. **Production Ready** - Handles edge cases and errors properly