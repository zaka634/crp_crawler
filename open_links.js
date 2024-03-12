function main() {
	var items = document.querySelectorAll("a.underline.text-blue-400").forEach((item) => window.open(item.href));
}


// build and open links.
case_numbers = [
    "MSC2490059742", "MSC2490059745"
]
function openBuildLink(caseNumber) {
    window.open(`https://www.casestatusext.com/cases/${caseNumber}`, '_blank');
}

caseNumbers.forEach(caseNumber => {
    openBuildLink(caseNumber);
});
