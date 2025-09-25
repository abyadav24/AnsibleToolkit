#!/usr/bin/expect -f

# Define variables (Replace with actual values or pass as arguments)
set ip "10.76.32.241"
set username "ADMIN"
set password "ADMIN"
set timeout 20

# Start the IPMI SOL session
spawn ipmitool -I lanplus -H $ip -U $username -P $password sol activate

# Wait for the SOL session to become operational
expect {
    "SOL Session operational" { send "\r" }
    timeout { puts "Failed to activate SOL session"; exit 1 }
}

# Small delay to ensure the session is stable
sleep 2

# Handle Ubuntu login prompt
expect {
    "ubuntu login:" {
        send "ubuntu\r"
        exp_continue
    }
    "Password:" {
        send "\r"
    }
}

# Run the script once after logging in
expect "$ " {
    send "sh /tmp/X710-T4L_for_OCP_3.0.sh\r"
}

# Wait for the script to finish executing (adjust time if needed)
sleep 1

# Exit the SOL session using the escape sequence (~.)
send "~.\r"

# Ensure EOF handling
expect eof

