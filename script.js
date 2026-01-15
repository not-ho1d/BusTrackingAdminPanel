var currentTool = null;

function log(msg){
    console.log(msg)
}
function main(){
    const toolSelector = document.querySelectorAll(".item");
    const editorDivs = document.querySelectorAll(".editor");
    const dropdownButton = document.querySelectorAll(".dropdown-btn");
    const dropdownMenu = document.querySelectorAll(".dropdown-menu");

    //make dropdown show up when clicked and remove editor interface
    dropdownMenu[0].style.display = "none";
    dropdownButton[0].addEventListener("click",(e)=>{
        if(dropdownMenu[0].style.display=="none"){
            dropdownMenu[0].style.display="block";
        }else{
            dropdownMenu[0].style.display="none";
        }
        if(currentTool != null)
            currentTool.style.display = "block" ? "none" : "block" ;
    })
    //hides all editor interface divs  
    editorDivs.forEach(div => {
        div.style.display = "none";
    })


    toolSelector.forEach(tool => {
        tool.addEventListener("click",(e)=>{
            let clickedButton = e.target.innerText;
            let matchingDiv = null;
            if(clickedButton == "View Routes"){
                matchingDiv = document.getElementById("ViewRoutesDiv");
                matchingDiv.style.display = "block"
                currentTool = matchingDiv;
            }else if(clickedButton == "Add Route"){
                matchingDiv = document.getElementById("AddRouteDiv");
                matchingDiv.style.display = "block"
                currentTool = matchingDiv;
            }else if(clickedButton == "Delete Route"){
                matchingDiv = document.getElementById("DeleteRouteDiv");
                matchingDiv.style.display = "block"
                currentTool = matchingDiv;
            }else if(clickedButton == "Edit Route"){
                matchingDiv = document.getElementById("EditRouteDiv");
                matchingDiv.style.display = "block"
                currentTool = matchingDiv;
            }else if(clickedButton == "Add Stop"){
                matchingDiv = document.getElementById("AddStopDiv");
                matchingDiv.style.display = "block"
                currentTool = matchingDiv;
            }
            dropdownMenu[0].style.display="none"
        })
    });
}
document.addEventListener("DOMContentLoaded",()=>{
    main();
})