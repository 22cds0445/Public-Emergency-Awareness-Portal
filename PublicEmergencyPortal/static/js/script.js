document.addEventListener("DOMContentLoaded", async () => {
    const searchDropdown = document.getElementById("search");
    const response = await fetch("/autocomplete");
    const townships = await response.json();
    townships.forEach(township => {
        const option = document.createElement("option");
        option.value = township;
        option.textContent = township;
        searchDropdown.appendChild(option);
    });
    const ctx = document.getElementById("callsChart").getContext("2d");
    fetch("/chart-data")
        .then(response => response.json())
        .then(data => {
            new Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: "Emergency Calls by Reason",
                        data: data.values,
                        backgroundColor: [
                            "#ff6384", "#36a2eb", "#ffcd56", "#4bc0c0", "#9966ff"
                        ],
                        hoverOffset: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "bottom"
                        }
                    }
                }
            });
        });
});