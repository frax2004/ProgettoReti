while [ 1 ]; do tc -j -s qdisc show dev h1-eth0 | jq 'map(. + {timestamp: (now | todate)})'; sleep 1; done
