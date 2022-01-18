package com.dfscn.mdw.oidc;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class LogoutApplication {
	
	@GetMapping("/logout")
	public String logout(){
		return "logout";
	}
	
}
