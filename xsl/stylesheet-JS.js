//Function which scrolls to the top of the page
function toTop(){
    document.body.scrollTop = document.documentElement.scrollTop = 0;
}

//Function checks where the page is scrolled to and either shows or hides the button which jumps to the top.
//If the page is scrolled within 30px of the top, the button is hidden (it is hidden when the page loads).
function showButtonOnScroll() {
    if (document.body.scrollTop > 30 || document.documentElement.scrollTop > 30) {
        document.getElementById("to_top_button").style.display = "block";
    } 
    else {
        document.getElementById("to_top_button").style.display = "none";
    }
}